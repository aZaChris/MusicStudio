"""Esportazione per la famiglia (GDPR, accesso e portabilità): tutto ciò che abbiamo su un account.

L'ambito si decide qui da chi è l'account, mai da un id nella richiesta: un genitore riceve i
figli collegati, uno studente adulto il proprio record. Quindi non c'è un id da manipolare
(docs/learning/concetti/isolamento-tenant-e-bola.md, gdpr-per-sviluppatori.md).
"""

from typing import Any

from django.db.models import Prefetch, QuerySet

from apps.accounts import mfa
from apps.accounts.models import Invitation, User
from apps.audit.models import AuditEntry
from apps.lessons.models import Lesson
from apps.notifications.models import ReminderDelivery
from apps.packages.models import Package
from apps.payments.models import (
    CheckoutSession,
    Payment,
    PaymentInstructions,
    StudioPaymentAccount,
)
from apps.students.models import Student

from .models import ConsentRecord


def students_of(user: User) -> QuerySet[Student]:
    # Lo studente adulto vede solo se stesso; il genitore i figli collegati. Gli altri ruoli non
    # arrivano qui (la view lo vieta), e comunque otterrebbero un elenco vuoto.
    if user.role == User.Role.STUDENT:
        return Student.objects.filter(user=user)
    return Student.objects.filter(parent_accounts__user=user)


def _studio_block(user: User) -> dict[str, Any]:
    # Per il titolare: il suo studio e le istruzioni di pagamento (decifrate: sono suoi dati).
    # Degli studenti e dei pagamenti non si aggiunge nulla: i conti dello studio non sono dati
    # personali del titolare (specs/008-cash-register-receipts/research.md, R15).
    from apps.studios.models import Teacher

    teacher = Teacher.objects.select_related("studio").filter(user=user, is_owner=True).first()
    if teacher is None:
        return {}
    instructions = PaymentInstructions.objects.filter(studio=teacher.studio).first()
    account = StudioPaymentAccount.objects.filter(studio=teacher.studio).first()
    return {
        "name": teacher.studio.name,
        # Fase 9: solo l'id del conto Stripe e il suo stato; il resto sta su Stripe, non da noi.
        "payment_account": None
        if account is None
        else {"stripe_account_id": account.stripe_account_id, "state": account.state},
        "payment_instructions": None
        if instructions is None
        else {
            "account_holder": instructions.account_holder,
            "iban": instructions.iban,
            "bank_name": instructions.bank_name,
            "note": instructions.note,
            "links": instructions.links,
        },
    }


def _receipt_number(payment: Payment) -> str | None:
    receipt = getattr(payment, "receipt", None)  # OneToOne inverso: assente se non emessa
    return None if receipt is None else f"{receipt.year}-{receipt.sequence:04d}"


def build_export(user: User) -> dict[str, Any]:
    # Sincrono: misurato il 2026-11-25 con 1 genitore, 3 figli e 2 anni di lezioni settimanali
    # (312 lezioni, 78 pagamenti, 85 KB) in 47-167 ms, contro un limite di 10 s (ADR-042).
    # FUTURO (export in background): un task Celery con link a scadenza, solo se un account
    # reale si avvicina al limite.
    # Una query per tabella (prefetch), non una per figlio: il costo non cresce con il numero
    # di figli. L'ordine è fisso così due esportazioni dello stesso account sono uguali.
    children = list(
        students_of(user)
        .select_related("studio")
        .prefetch_related(
            Prefetch("lessons", queryset=Lesson.objects.order_by("start_time")),
            Prefetch("packages", queryset=Package.objects.order_by("purchase_date", "id")),
            Prefetch(
                "payments",
                queryset=Payment.objects.select_related("receipt").order_by("date", "id"),
            ),
        )
        .order_by("id")
    )
    consents = ConsentRecord.objects.filter(parent__user=user).prefetch_related("students")
    # Fase 10 (ADR-042): le tabelle che l'export del 2026 non copriva, una query ciascuna.
    reminders = ReminderDelivery.objects.filter(parent__user=user).order_by("created_at", "id")
    checkouts = CheckoutSession.objects.filter(created_by=user).order_by("created_at")
    # Solo gli inviti rivolti all'indirizzo della persona: quelli che ha mandato contengono le
    # email di altri, che non sono dati suoi.
    invitations = (
        Invitation.objects.filter(email__iexact=user.email)
        .select_related("studio")
        .order_by("created_at", "id")
    )
    # Diritto di accesso: ciò che il registro dice delle sue azioni, non di quelle degli altri.
    activity = AuditEntry.objects.filter(actor=user).order_by("created_at", "id")
    # Solo dati dell'account e dei figli collegati. Nessun dato di altri genitori o di altri studi.
    export: dict[str, Any] = {
        "account": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "preferred_language": user.preferred_language,
            "created_at": user.date_joined,
            "terms_accepted_at": user.terms_accepted_at,
            # Solo se il secondo fattore è attivo: il segreto e i codici non escono mai.
            "mfa_enabled": mfa.is_enabled(user),
        },
        "children": [
            {
                "id": s.pk,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "instrument": s.instrument,
                "studio": s.studio.name,
                "is_active": s.is_active,
                # Dopo una cancellazione resta il record anonimizzato: l'export lo dice.
                "anonymised_at": s.anonymised_at,
                "lessons": [
                    {
                        "id": lesson.pk,
                        "start_time": lesson.start_time,
                        "end_time": lesson.end_time,
                        "status": lesson.status,
                        "notes": lesson.notes,
                    }
                    for lesson in s.lessons.all()
                ],
                "packages": [
                    {
                        "id": p.pk,
                        "total_lessons": p.total_lessons,
                        "lessons_remaining": p.lessons_remaining,
                        "purchase_date": p.purchase_date,
                        "expiry_date": p.expiry_date,
                        "price": p.price,
                    }
                    for p in s.packages.all()
                ],
                "payments": [
                    {
                        "id": pay.pk,
                        "amount": pay.amount,
                        "date": pay.date,
                        "method": pay.method,
                        "status": pay.status,
                        "reversal_of": pay.reversal_of_id,
                        # La ricevuta si cita col suo numero: il PDF si genera a richiesta.
                        "receipt_number": _receipt_number(pay),
                    }
                    for pay in s.payments.all()
                ],
            }
            for s in children
        ],
        "consents": [
            {
                "id": c.pk,
                "notice_version": c.notice_version,
                "given_at": c.given_at,
                "withdrawn_at": c.withdrawn_at,
                "children": [s.pk for s in c.students.all()],
            }
            for c in consents
        ],
        "reminders": [
            {"lesson": r.lesson_id, "status": r.status, "sent_at": r.sent_at} for r in reminders
        ],
        "online_checkouts": [
            {
                "amount": c.amount,
                "currency": c.currency,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in checkouts
        ],
        "invitations": [
            {
                "studio": i.studio.name,
                "role": i.role,
                "status": i.status,
                "created_at": i.created_at,
            }
            for i in invitations
        ],
        "activity": [
            {"created_at": a.created_at, "action": a.action, "outcome": a.outcome} for a in activity
        ],
    }
    # Solo per il titolare: il suo studio e le istruzioni di pagamento (fase 8, FR-023).
    if user.role == User.Role.STUDIO_OWNER:
        export["studio"] = _studio_block(user)
    return export
