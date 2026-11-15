"""Promemoria delle lezioni con una outbox transazionale (ADR-015, sostituisce ADR-008).

1. Lo sweep (ogni 15 minuti) trova le lezioni a circa 24 ore di distanza e, in una sola
   transazione, segna la lezione come già vista e inserisce un `ReminderDelivery` per ogni
   genitore collegato. Rieseguirlo, o due sweep sovrapposti, non può duplicare righe:
   `UNIQUE (lesson, parent)`.
2. Ogni invio parte da un task suo. L'invio si prende in carico con un UPDATE condizionale
   (pending, oppure "sending" con la lease scaduta), si spedisce, poi si segna come inviato.
   Se fallisce torna a pending e il task riprova con backoff esponenziale.

Garanzia: almeno una volta, senza doppioni per (lesson, parent). L'unica finestra di doppione
rimasta è un crash dopo che il server SMTP ha accettato la email e prima di segnarla come
inviata. Exactly-once con SMTP è impossibile: questa finestra dura millisecondi invece di
"per sempre". Spiegazione: docs/learning/concetti/task-celery-idempotenti.md.
"""

import datetime
import logging

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Prefetch, Q, QuerySet
from django.template.loader import render_to_string
from django.utils import timezone

from apps.lessons.models import Lesson
from apps.students.models import ParentStudentLink

from .models import ReminderDelivery

logger = logging.getLogger(__name__)

# Finestra dello sweep: lezioni tra 23h45 e 24h da adesso. Ogni 15 minuti la finestra scorre di
# 15 minuti, quindi ogni lezione ci passa dentro una volta sola.
REMINDER_WINDOW_START = datetime.timedelta(hours=23, minutes=45)
REMINDER_WINDOW_END = datetime.timedelta(hours=24)
# Quanto un invio può restare "sending" prima che un altro worker lo riprenda.
LEASE = datetime.timedelta(minutes=10)
MAX_ATTEMPTS = 5  # primo invio più quattro tentativi (vedi tasks.py)


class DeliveryFailed(Exception):
    """La email non è partita: l'invio è tornato a pending per un nuovo tentativo."""


def due_lessons(now: datetime.datetime) -> QuerySet[Lesson]:
    # Lezioni in programma nella finestra e non ancora viste da uno sweep. I collegamenti con i
    # genitori si caricano in anticipo (prefetch) per non fare una query per lezione.
    return Lesson.objects.filter(
        status=Lesson.Status.SCHEDULED,
        start_time__gte=now + REMINDER_WINDOW_START,
        start_time__lt=now + REMINDER_WINDOW_END,
        reminder_sent_at__isnull=True,
    ).prefetch_related(
        Prefetch("student__parentstudentlink_set", queryset=ParentStudentLink.objects.all())
    )


def enqueue_due_reminders(now: datetime.datetime | None = None) -> int:
    """Registra gli invii di ogni lezione dovuta. Restituisce quante lezioni ha elaborato."""
    now = now or timezone.now()
    swept = 0
    for lesson in due_lessons(now):
        with transaction.atomic():
            claimed = Lesson.objects.filter(pk=lesson.pk, reminder_sent_at__isnull=True).update(
                reminder_sent_at=now
            )
            # UPDATE condizionale: vince un solo sweep, l'altro vede 0 righe e passa oltre.
            if not claimed:
                continue  # uno sweep sovrapposto è arrivato prima
            ReminderDelivery.objects.bulk_create(
                [
                    ReminderDelivery(lesson_id=lesson.pk, parent_id=link.parent_id)
                    for link in lesson.student.parentstudentlink_set.all()
                ],
                ignore_conflicts=True,
            )
        swept += 1
    return swept


def deliveries_to_send(now: datetime.datetime | None = None) -> list[int]:
    """Invii pendenti, più quelli il cui worker è morto tenendo la lease. Al massimo 500 a giro."""
    now = now or timezone.now()
    stale = Q(status=ReminderDelivery.Status.SENDING, claimed_at__lt=now - LEASE)
    return list(
        ReminderDelivery.objects.filter(Q(status=ReminderDelivery.Status.PENDING) | stale)
        .order_by("id")
        .values_list("id", flat=True)[:500]
    )


def _claim(delivery_id: int, now: datetime.datetime) -> bool:
    # Presa in carico atomica: un solo UPDATE condizionale. Se restituisce 1 riga l'invio è
    # nostro, altrimenti ce l'ha già qualcun altro. Nessun lock esplicito, nessuna gara.
    claimable = Q(status=ReminderDelivery.Status.PENDING) | Q(
        status=ReminderDelivery.Status.SENDING, claimed_at__lt=now - LEASE
    )
    return (
        ReminderDelivery.objects.filter(claimable, pk=delivery_id).update(
            status=ReminderDelivery.Status.SENDING, claimed_at=now, attempts=F("attempts") + 1
        )
        == 1
    )


def send_delivery(delivery_id: int) -> str:
    """Prende in carico, invia, segna. Restituisce l'esito.

    Solleva DeliveryFailed se l'invio fallisce.
    """
    now = timezone.now()
    if not _claim(delivery_id, now):
        return "not-claimable"  # già inviato, oppure un altro tiene una lease ancora valida
    delivery = ReminderDelivery.objects.select_related("lesson__student", "parent__user").get(
        pk=delivery_id
    )
    # La lezione può essere stata annullata o svolta tra lo sweep e l'invio: allora non si scrive.
    if delivery.lesson.status != Lesson.Status.SCHEDULED:
        _set(delivery_id, ReminderDelivery.Status.SKIPPED)
        return "skipped"
    recipient = delivery.parent.user
    # FUTURO (lingua dei messaggi): il corpo segue `preferred_language` dell'utente, ma l'oggetto
    # qui sotto è sempre in inglese. Localizzare anche l'oggetto con lo stesso criterio.
    body = render_to_string(
        f"notifications/reminder_email_{recipient.preferred_language}.txt",
        {
            "student_name": delivery.lesson.student.full_name,
            "start_time": delivery.lesson.start_time,
        },
    )
    try:
        send_mail(
            subject="Upcoming lesson reminder — MusicStudio",
            message=body,
            from_email=None,
            recipient_list=[recipient.email],
        )
    except Exception as exc:
        _set(delivery_id, ReminderDelivery.Status.PENDING, error=str(exc))
        raise DeliveryFailed(str(exc)) from exc
    ReminderDelivery.objects.filter(pk=delivery_id).update(
        status=ReminderDelivery.Status.SENT, sent_at=timezone.now(), last_error=""
    )
    return "sent"


def give_up(delivery_id: int, error: str) -> None:
    # Ultimo tentativo fallito: l'invio passa a FAILED e resta visibile nell'admin e nei log
    # (Sentry, ADR-019) invece di riprovare all'infinito.
    logger.error("Reminder delivery %s failed permanently: %s", delivery_id, error)
    _set(delivery_id, ReminderDelivery.Status.FAILED, error=error)


def _set(delivery_id: int, status: str, *, error: str = "") -> None:
    # L'errore si tronca a 1000 caratteri per non riempire la tabella.
    ReminderDelivery.objects.filter(pk=delivery_id).update(status=status, last_error=error[:1000])
