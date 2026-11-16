"""Consenso, esportazione e cancellazione (constitution X, ADR-032).

La cancellazione è un'anonimizzazione sul posto: ciò che lo studio deve conservare (importi e
date di pagamenti e lezioni) resta, senza nomi e testi liberi, così i conti dello studio
tornano ancora. Spiegazione: docs/learning/concetti/gdpr-per-sviluppatori.md.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.accounts import services as account_services
from apps.accounts.models import Invitation, MfaDevice, User
from apps.audit import services as audit
from apps.common.exceptions import DomainConflict
from apps.lessons.models import Lesson
from apps.payments.models import (
    CheckoutSession,
    Payment,
    PaymentInstructions,
    StudioPaymentAccount,
)
from apps.students.models import ParentAccount, ParentStudentLink, Student

from . import selectors
from .models import ConsentRecord


def give_consent(parent: ParentAccount, students: Iterable[Student]) -> ConsentRecord:
    # Registra il consenso con la versione corrente dell'informativa e lo scrive nel registro
    # delle azioni, una voce per ogni studio coinvolto (i figli possono stare in studi diversi).
    students = list(students)
    record = ConsentRecord.objects.create(
        parent=parent, notice_version=settings.PRIVACY_NOTICE_VERSION
    )
    record.students.set(students)
    for studio_id in {s.studio_id for s in students}:
        audit.record(
            audit.Action.CONSENT_GIVE,
            actor=parent.user,
            target=record,
            studio_id=studio_id,
            metadata={"notice_version": settings.PRIVACY_NOTICE_VERSION},
        )
    return record


class CheckoutOpen(DomainConflict):
    # Non si cancella con un pagamento online ancora aperto: va prima concluso.
    code = "checkout_open"


class StudioNotEmpty(DomainConflict):
    # Il titolare non può chiudere l'account finché lo studio ha studenti.
    code = "studio_not_empty"


def anonymise_student(student: Student) -> None:
    """Sostituisce i dati personali di un allievo.

    Lezioni, pacchetti e pagamenti tengono gli importi. La riga dello studente resta, così le
    chiavi esterne non si rompono. Le note delle lezioni (testo libero, possono contenere dati
    personali) vengono svuotate.
    """
    student.first_name = "Allievo"
    student.last_name = f"cancellato #{student.pk}"
    student.instrument = ""
    student.is_active = False
    student.user = None
    student.anonymised_at = timezone.now()
    student.save()
    Lesson.objects.filter(student=student).update(notes="")


def _check_password(user: User, password: str) -> None:
    # Operazione distruttiva: si riconferma la password anche con la sessione aperta.
    if not user.check_password(password):
        raise ValidationError({"password": "Wrong password."})


def _release_children(user: User, children: list[Student]) -> list[Student]:
    """Scollega `user` da `children`; anonimizza i figli a cui non resta nessun altro genitore.

    Restituisce i figli che restano perché c'è ancora un altro genitore.
    """
    parent = ParentAccount.objects.filter(user=user).first()
    kept: list[Student] = []
    for child in children:
        others = ParentStudentLink.objects.filter(student=child)
        if parent is not None:
            others = others.exclude(parent=parent)
        if others.exists():
            kept.append(child)
        else:
            anonymise_student(child)
    if parent is not None:
        ParentStudentLink.objects.filter(parent=parent, student__in=children).delete()
    return kept


def _notify_teachers(kept: list[Student]) -> None:
    # `on_commit`: l'avviso parte solo se la transazione va a buon fine, mai per una
    # cancellazione poi annullata. Import locale per evitare un import circolare.
    from .tasks import notify_parent_left

    for child in kept:
        transaction.on_commit(partial(notify_parent_left.delay, child.pk))


@transaction.atomic
def erase_account(user: User, password: str) -> None:
    """Chiude l'account e cancella o anonimizza ciò che ne dipende (genitore, studente adulto).

    Tutto in una transazione: o si fa tutto o niente. L'utente non viene eliminato ma svuotato
    (email e username fittizi, password inutilizzabile): resta una riga anonima (ADR-032).
    """
    _check_password(user, password)
    # Un titolare con studenti non può sparire lasciando lo studio senza responsabile.
    if user.role == User.Role.STUDIO_OWNER:
        from apps.studios.models import Teacher

        if (
            Student.objects.filter(studio__teachers__user=user).exists()
            and Teacher.objects.filter(user=user, is_owner=True).exists()
        ):
            raise StudioNotEmpty("The studio still has students.")
        # Le istruzioni di pagamento (IBAN) sono dati del titolare: se ne vanno con l'account.
        PaymentInstructions.objects.filter(
            studio__teachers__user=user, studio__teachers__is_owner=True
        ).delete()
        # Il legame col conto Stripe (fase 9) va via con l'account; il conto resta di chi lo ha
        # aperto su Stripe, che è un altro rapporto: MusicStudio non lo chiude né lo tocca.
        StudioPaymentAccount.objects.filter(
            studio__teachers__user=user, studio__teachers__is_owner=True
        ).delete()
    children = list(selectors.students_of(user))
    if CheckoutSession.objects.filter(
        package__student__in=children, status=CheckoutSession.Status.OPEN
    ).exists():
        raise CheckoutOpen("An online payment is still pending.")
    # Gli studi si salvano prima di scollegare i figli: servono per il registro delle azioni.
    studio_ids = {c.studio_id for c in children}
    old_email = user.email
    kept = _release_children(user, children)
    if user.role == User.Role.STUDENT:
        # Il record dello studente adulto se ne va con il suo account.
        for child in children:
            anonymise_student(child)
    ConsentRecord.objects.filter(parent__user=user).delete()
    Invitation.objects.filter(email__iexact=old_email).delete()
    Invitation.objects.filter(accepted_by=user).delete()
    MfaDevice.objects.filter(user=user).delete()
    # Sessioni chiuse subito: i token già emessi non devono restare validi (ADR-018).
    account_services.revoke_all_sessions(user)
    OutstandingToken.objects.filter(user=user).delete()
    ParentAccount.objects.filter(user=user).delete()
    marker = uuid.uuid4().hex
    user.first_name = ""
    user.last_name = ""
    user.email = f"erased-{marker}@invalid"
    user.username = f"erased-{marker}"
    user.is_active = False
    user.set_unusable_password()
    user.save()
    ids: list[int | None] = list(studio_ids) or [None]
    for studio_id in ids:
        audit.record(audit.Action.PRIVACY_ERASE, actor=user, target=user, studio_id=studio_id)
    _notify_teachers(kept)


@transaction.atomic
def withdraw_consent(user: User, consent_id: int, password: str) -> None:
    """Ritirare il consenso toglie i figli interessati dal lato del genitore: il genitore viene
    scollegato, e un figlio senza altri genitori viene anonimizzato."""
    _check_password(user, password)
    consent = ConsentRecord.objects.filter(
        pk=consent_id, parent__user=user, withdrawn_at__isnull=True
    ).first()
    if consent is None:
        raise Http404
    children = list(consent.students.all())
    if CheckoutSession.objects.filter(
        package__student__in=children, status=CheckoutSession.Status.OPEN
    ).exists():
        raise CheckoutOpen("An online payment is still pending.")
    kept = _release_children(user, children)
    consent.withdrawn_at = timezone.now()
    consent.save(update_fields=["withdrawn_at"])
    for studio_id in {c.studio_id for c in children}:
        audit.record(
            audit.Action.CONSENT_WITHDRAW,
            actor=user,
            target=consent,
            studio_id=studio_id,
        )
    _notify_teachers(kept)


# --- Conservazione (ADR-032) --------------------------------------------------------------
# FUTURO (conservazione contabile): i 10 anni dei pagamenti sono da confermare con un
# commercialista prima di considerarli definitivi.
ARCHIVED_STUDENT = timedelta(days=730)  # 24 mesi dopo l'ultima attività
PAYMENTS = timedelta(days=3650)  # 10 anni, conservazione contabile da confermare
AUDIT = timedelta(days=365)
UNCONFIRMED_SIGNUP = timedelta(days=7)


def run_retention(now: datetime | None = None) -> dict[str, int]:
    """Pulizia giornaliera dei dati oltre il periodo di conservazione; restituisce le righe toccate.

    Si può lanciare due volte senza danni: ogni regola tocca solo righe ancora oltre il limite.
    """
    now = now or timezone.now()
    # Studenti archiviati, non ancora anonimi, senza attività né lezioni recenti.
    cutoff = now - ARCHIVED_STUDENT
    stale = Student.objects.filter(
        is_active=False, anonymised_at__isnull=True, updated_at__lt=cutoff
    ).exclude(lessons__start_time__gte=cutoff)
    students = list(stale.distinct())
    for student in students:
        anonymise_student(student)
    payments, _ = Payment.objects.filter(date__lt=(now - PAYMENTS).date()).delete()
    return {
        "students_anonymised": len(students),
        "payments_deleted": payments,
        "audit_deleted": audit.purge_older_than(now - AUDIT),
        "signups_deleted": account_services.purge_unconfirmed(now - UNCONFIRMED_SIGNUP),
    }
