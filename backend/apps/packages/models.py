"""Modello del pacchetto di lezioni di uno studente.

Il saldo (`lessons_remaining`) vive nel database con un vincolo di coerenza, non solo nel codice:
vedi docs/learning/concetti/service-layer-e-modular-monolith.md e ADR-002.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.students.models import Student


class Package(models.Model):
    # Un blocco di lezioni comprato da uno studente. Lo studio si ricava dallo studente:
    # non c'è una colonna `studio` duplicata che potrebbe andare fuori sincrono (ADR-010).
    class Status(models.TextChoices):
        # Stati calcolati dalla property `status`, mai salvati.
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        COMPLETED = "completed", "Completed"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="packages")
    total_lessons = models.PositiveSmallIntegerField()
    # Gestito dal sistema: lo imposta packages.services.create_package e lo scala solo
    # lessons.services.complete_lesson. In sola lettura dall'API.
    lessons_remaining = models.PositiveSmallIntegerField()
    purchase_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-purchase_date", "-id"]
        constraints = [
            # Rete di sicurezza nel database: il saldo non va mai sotto zero né sopra il totale,
            # anche se due richieste concorrenti o un bug nel codice provassero a violarlo.
            models.CheckConstraint(
                condition=models.Q(lessons_remaining__gte=0)
                & models.Q(lessons_remaining__lte=models.F("total_lessons")),
                name="package_remaining_within_total",
            )
        ]
        indexes = [
            # Indice parziale per "pacchetto attivo di uno studente": il più recente che ha ancora
            # lezioni. Indicizza solo le righe con saldo > 0, quindi resta piccolo
            # (docs/learning/concetti/indici-ed-explain.md).
            models.Index(
                fields=["student", "-purchase_date"],
                name="package_active_by_student_idx",
                condition=models.Q(lessons_remaining__gt=0),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.lessons_remaining}/{self.total_lessons}"

    def tenant_keys(self) -> tuple[int, int]:
        # (studio, insegnante) usati dai permessi per oggetto (CanWriteTenantObject, ADR-011).
        return self.student.studio_id, self.student.teacher_id

    @property
    def status(self) -> str:
        # Scaduto vince su completato: se la data è passata il pacchetto non si usa più.
        if self.expiry_date and self.expiry_date < timezone.localdate():
            return self.Status.EXPIRED
        if self.lessons_remaining == 0:
            return self.Status.COMPLETED
        return self.Status.ACTIVE

    @property
    def is_low(self) -> bool:
        # True se restano poche lezioni (soglia PACKAGE_LOW_THRESHOLD, default 2). Lo espone
        # il serializer, così il client può mostrare l'avviso "pacchetto quasi finito".
        threshold: int = getattr(settings, "PACKAGE_LOW_THRESHOLD", 2)
        return 0 < self.lessons_remaining <= threshold
