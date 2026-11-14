"""Modello della lezione: uno spazio nell'agenda, con vincoli che impediscono le sovrapposizioni.

Per studiare: docs/learning/concetti/exclusion-constraint.md e ADR-009 (sovrapposizioni
rifiutate dal database), docs/learning/concetti/indici-ed-explain.md (gli indici qui sotto),
docs/learning/concetti/cifratura-dei-campi.md e ADR-030 (le note).

FUTURO (metriche Sentry, vedi ADR-019): contare "lezione creata" e "lezione completata" con
le metriche applicative di Sentry (sentry_sdk.metrics), dentro services.py, non qui. Prima di
scrivere codice controllare il nome esatto dell'API nella documentazione dell'SDK in uso.
"""

import datetime

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.packages.models import Package
from apps.students.models import Student
from apps.studios.models import Teacher


class TsTzRange(models.Func):
    """SQL `tstzrange(start, end, '[)')`: un intervallo di tempo semiaperto.

    Semiaperto = include l'inizio ed esclude la fine: due lezioni una dopo l'altra
    (10:00-11:00 e 11:00-12:00) non si sovrappongono.
    """

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


# Stati che occupano uno spazio in agenda. Le lezioni annullate o con assenza lo liberano.
ACTIVE_STATUSES = ("scheduled", "completed")


class Lesson(models.Model):
    """Una lezione. I cambi di stato vivono in lessons.services (ADR-002)."""

    class Status(models.TextChoices):
        # Quattro stati: in programma, svolta, annullata, assente (no-show).
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="lessons")
    # L'insegnante è sempre quello dello studente (lo imposta create_lesson in services.py).
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="lessons")
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons"
    )
    start_time = models.DateTimeField()
    # Salvato e non calcolato in SQL: `timestamptz + interval` è STABLE e non IMMUTABLE, quindi
    # non può comparire nell'espressione d'indice del vincolo di esclusione (ADR-009).
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    # Testo libero su uno studente spesso minorenne: cifrato nel database (ADR-030).
    notes = EncryptedTextField(blank=True)
    # Quando è partito il promemoria. Lo scrive l'app notifications con lo schema "outbox"
    # (ADR-008 e ADR-015): serve a non mandare lo stesso promemoria due volte.
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]
        constraints = [
            # La fine deve venire dopo l'inizio.
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="lesson_end_after_start",
            ),
            # Il database stesso rifiuta due lezioni attive sovrapposte, anche se due richieste
            # arrivano nello stesso istante (un controllo nel codice andrebbe in "gara").
            # Un vincolo per l'insegnante e uno per lo studente.
            ExclusionConstraint(
                name="lesson_no_teacher_overlap",
                expressions=[
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("teacher", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=ACTIVE_STATUSES),
            ),
            ExclusionConstraint(
                name="lesson_no_student_overlap",
                expressions=[
                    (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("student", RangeOperators.EQUAL),
                ],
                condition=models.Q(status__in=ACTIVE_STATUSES),
            ),
        ]
        indexes = [
            # Agenda settimanale, prossime lezioni, dashboard: WHERE teacher_id = ? AND
            # start_time in un intervallo.
            models.Index(fields=["teacher", "start_time"], name="lesson_teacher_start_idx"),
            # Giro dei promemoria: indice parziale, solo le lezioni in programma e non ancora
            # ricordate. Resta piccolo anche con anni di storico.
            models.Index(
                fields=["start_time"],
                name="lesson_reminder_due_idx",
                condition=models.Q(status="scheduled", reminder_sent_at__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} @ {self.start_time:%Y-%m-%d %H:%M}"

    def tenant_keys(self) -> tuple[int, int]:
        # Chiavi dei permessi per oggetto: (studio, insegnante). Vedi ADR-011 e
        # docs/learning/concetti/isolamento-tenant-e-bola.md.
        return self.student.studio_id, self.teacher_id

    @property
    def duration_minutes(self) -> int:
        # Si confronta in UTC: sottrarre due datetime con lo stesso fuso è aritmetica "da
        # orologio" e sbaglia nelle notti del cambio d'ora.
        elapsed = self.end_time.astimezone(datetime.UTC) - self.start_time.astimezone(datetime.UTC)
        return int(elapsed.total_seconds() // 60)
