"""Scritture sulle lezioni (percorsi critici per il business, principio III della costituzione).

Tre idee da conoscere prima di toccare questo file:
1. Le sovrapposizioni le rifiuta il database, non il codice (docs/learning/concetti/
   exclusion-constraint.md, ADR-009): qui si traduce solo l'errore in un 409.
2. Le durate si calcolano in UTC (`end_of`), mai con l'orologio locale.
3. Completare una lezione scala il pacchetto una volta sola, anche con doppio clic.
Il perché del livello "services": docs/learning/concetti/service-layer-e-modular-monolith.md.
"""

import datetime
from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F
from django.utils import timezone
from psycopg.errors import DeadlockDetected

from apps.common.exceptions import DomainConflict
from apps.packages.models import Package
from apps.students.models import Student

from .models import Lesson


class LessonOverlapError(DomainConflict):
    """Lo spazio in agenda è già occupato da una lezione attiva (HTTP 409)."""

    code = "lesson_overlap"


# Nome del vincolo → messaggio. La regola la impone il database (ADR-009); noi traduciamo.
OVERLAP_MESSAGES = {
    "lesson_no_teacher_overlap": "The teacher already has a lesson in this time slot.",
    "lesson_no_student_overlap": "The student already has a lesson in this time slot.",
}


# Due inserimenti simultanei nello stesso spazio possono andare in deadlock sul vincolo di
# esclusione: ogni transazione inserisce la sua riga, poi aspetta quella non ancora
# confermata dell'altra mentre controlla. PostgreSQL ne annulla una (SQLSTATE 40P01). Basta
# riprovare la perdente: al secondo giro vede la riga della vincente e ottiene una normale
# violazione del vincolo → 409. Il caso è nei "Gotchas" di CLAUDE.md.
MAX_DEADLOCK_RETRIES = 2


def _guarded_write[T](write: Callable[[], T]) -> T:
    """Esegue una scrittura di lezione in un savepoint; traduce le sovrapposizioni in 409.

    Il savepoint lascia utilizzabile la transazione esterna dopo l'errore.
    """
    for attempt in range(MAX_DEADLOCK_RETRIES + 1):
        try:
            with transaction.atomic():
                return write()
        except IntegrityError as exc:
            # Il nome del vincolo violato sta nei dettagli dell'errore di psycopg.
            diag = getattr(exc.__cause__, "diag", None)
            constraint = getattr(diag, "constraint_name", None)
            if constraint in OVERLAP_MESSAGES:
                raise LessonOverlapError(OVERLAP_MESSAGES[constraint]) from exc
            raise
        except OperationalError as exc:
            # Deadlock: si riprova (fino a MAX_DEADLOCK_RETRIES); altri errori risalgono.
            if isinstance(exc.__cause__, DeadlockDetected) and attempt < MAX_DEADLOCK_RETRIES:
                continue
            raise
    raise AssertionError("unreachable")  # pragma: no cover


def end_of(start: datetime.datetime, minutes: int) -> datetime.datetime:
    """Fine reale di una lezione.

    Python somma un timedelta a un datetime con fuso sull'*orologio da parete* di quel fuso.
    DRF ci passa datetime Europe/Rome, quindi nella notte in cui le lancette tornano indietro
    02:30 CEST + 60 minuti darebbe 03:30 CET, cioè due ore reali dopo. Calcolando in UTC si
    evita l'errore.
    """
    return start.astimezone(datetime.UTC) + datetime.timedelta(minutes=minutes)


def _ensure_package_matches_student(student: Student, package: Package | None) -> None:
    # Lo scoping da solo permetterebbe un altro studente dello stesso insegnante; completare
    # quella lezione scalerebbe il pacchetto della famiglia sbagliata.
    if package is not None and package.student_id != student.pk:
        raise ValidationError({"package": "Package must belong to the lesson's student."})


def create_lesson(
    *,
    student: Student,
    start_time: datetime.datetime,
    duration_minutes: int = 30,
    package: Package | None = None,
    notes: str = "",
) -> Lesson:
    """Crea una lezione. L'insegnante è sempre quello dello studente; il pacchetto, se non
    indicato, è quello attivo dello studente."""
    if package is None:
        package = student.active_package
    _ensure_package_matches_student(student, package)
    return _guarded_write(
        lambda: Lesson.objects.create(
            student=student,
            teacher=student.teacher,
            package=package,
            start_time=start_time,
            end_time=end_of(start_time, duration_minutes),
            notes=notes,
        )
    )


def update_lesson(lesson: Lesson, **changes: Any) -> Lesson:
    """Modifica una lezione e ricalcola la fine da inizio e durata."""
    duration = changes.pop("duration_minutes", lesson.duration_minutes)
    for field, value in changes.items():
        setattr(lesson, field, value)
    lesson.end_time = end_of(lesson.start_time, duration)
    if "student" in changes:
        lesson.teacher = lesson.student.teacher
    _ensure_package_matches_student(lesson.student, lesson.package)
    _guarded_write(lesson.save)
    return lesson


@transaction.atomic
def complete_lesson(lesson: Lesson, *, note: str = "") -> Lesson:
    """Segna la lezione come svolta e scala il suo pacchetto esattamente una volta.

    Idempotente e sicura con più richieste insieme: la riga della lezione è bloccata, quindi
    un doppio invio aspetta il primo e poi trova `completed`. Lo scalo del pacchetto è un
    singolo UPDATE con guardia che non può mai scendere sotto zero.
    """
    locked = Lesson.objects.select_for_update().get(pk=lesson.pk)
    if locked.status == Lesson.Status.COMPLETED:
        return locked

    locked.status = Lesson.Status.COMPLETED
    if note:
        locked.notes = note
    # Una lezione annullata rientra in agenda quando viene completata: il suo spazio
    # potrebbe essere stato preso nel frattempo (da qui `_guarded_write`).
    _guarded_write(lambda: locked.save(update_fields=["status", "notes", "updated_at"]))

    if locked.package_id is not None:
        # Il filtro lessons_remaining__gt=0 è la guardia "mai sotto zero".
        Package.objects.filter(pk=locked.package_id, lessons_remaining__gt=0).update(
            lessons_remaining=F("lessons_remaining") - 1, updated_at=timezone.now()
        )
    return locked


# Gli stati che l'API consente per annullare (usati anche dal serializer).
CANCEL_STATUSES = (Lesson.Status.CANCELLED, Lesson.Status.NO_SHOW)


def cancel_lesson(lesson: Lesson, *, status: str) -> Lesson:
    """Annulla o segna l'assenza. Una lezione svolta resta svolta (il pacchetto non si rimborsa)."""
    if status not in CANCEL_STATUSES:
        raise ValidationError({"status": "Status must be 'cancelled' or 'no_show'."})
    if lesson.status == Lesson.Status.COMPLETED:
        return lesson
    lesson.status = status
    lesson.save(update_fields=["status", "updated_at"])
    return lesson
