"""Studente, account genitore e collegamento genitore-studente.

Spiegazione: docs/learning/concetti/multi-tenancy.md (isolamento per studio) e
docs/learning/concetti/gdpr-per-sviluppatori.md (anonimizzazione).
"""

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models

from apps.studios.models import Studio, Teacher

if TYPE_CHECKING:
    from apps.packages.models import Package

# Nome dell'attributo riempito da students.selectors.active_packages_prefetch().
ACTIVE_PACKAGES_ATTR = "active_packages"


class Student(models.Model):
    # Chi prende lezioni. Il dato personale più delicato dell'app (spesso un minore).
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    instrument = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="students")
    # Tenant dello studente e di tutto ciò che ne dipende (lezioni, pacchetti, pagamenti).
    # Sempre uguale a teacher.studio; lo imposta students.services (ADR-010). È duplicato di
    # proposito: filtrare per studio direttamente evita un join in ogni query.
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT, related_name="students")
    is_active = models.BooleanField(default=True)
    # Lo imposta l'insegnante. Solo gli adulti possono avere un account proprio; i minori si
    # raggiungono tramite un genitore. Un flag e non la data di nascita: minimizzazione dei dati
    # (constitution X).
    is_adult = models.BooleanField(default=False, db_default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
    )
    # Valorizzato quando la cancellazione o la conservazione hanno sostituito i dati personali
    # (ADR-032): la riga resta, con i dati anonimi.
    anonymised_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def tenant_keys(self) -> tuple[int, int]:
        # (id studio, id insegnante responsabile): li usano i permessi per oggetto (ADR-011).
        return self.studio_id, self.teacher_id

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def active_package(self) -> "Package | None":
        # Il pacchetto più recente con lezioni rimaste. Usa la lista già caricata quando il
        # queryset viene da un selector (nessuna query); altrimenti fa una query sola (percorsi a
        # oggetto singolo, come la creazione).
        prefetched: list[Package] | None = getattr(self, ACTIVE_PACKAGES_ATTR, None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        return (
            self.packages.filter(lessons_remaining__gt=0).order_by("-purchase_date", "-id").first()
        )


class ParentAccount(models.Model):
    # Account di un genitore: vede gli studenti collegati, anche di studi diversi.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_account"
    )
    students = models.ManyToManyField(
        Student, through="ParentStudentLink", related_name="parent_accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.email


class ParentStudentLink(models.Model):
    # Tabella intermedia esplicita genitore-studente. L'unicità evita collegamenti doppi.
    parent = models.ForeignKey(ParentAccount, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "student"], name="unique_parent_student_link")
        ]

    def __str__(self) -> str:
        return f"{self.parent} -> {self.student}"
