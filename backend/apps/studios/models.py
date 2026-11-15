"""Studio (il tenant, ADR-010) e insegnante.

Spiegazione: docs/learning/concetti/multi-tenancy.md.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Studio(models.Model):
    # Lo studio è l'unità di isolamento dei dati: ogni query filtra per studio (ADR-010).
    name = models.CharField(max_length=200)
    # Il titolare. SET_NULL e null=True perché studio e titolare si creano uno dopo l'altro
    # (ognuno punta all'altro): vedi create_solo_teacher in services.py.
    owner = models.OneToOneField(
        "studios.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_studio",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Teacher(models.Model):
    # Un insegnante è un utente con il ruolo teacher, agganciato a uno studio.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher"
    )
    # Ogni insegnante appartiene a un solo studio, il tenant (ADR-010). Un insegnante singolo
    # ha uno studio personale di una persona. PROTECT: cancellare uno studio non deve lasciare
    # dati orfani senza dirlo.
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT, related_name="teachers")
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Prima era un override di save() che chiamava clean(); ora lo garantisce il database
            # per qualsiasi scrittura (anche update in blocco e SQL diretto).
            models.CheckConstraint(
                condition=models.Q(is_owner=False) | models.Q(studio__isnull=False),
                name="teacher_owner_has_studio",
            )
        ]

    def __str__(self) -> str:
        return self.user.email

    def clean(self) -> None:
        # Validazione per form e admin. Il limite di insegnanti è in services.py, importato qui
        # dentro la funzione per evitare l'import circolare con questo modulo.
        if self.is_owner and self.studio_id is None:
            raise ValidationError("A studio owner must belong to a studio.")
        if self.studio_id is not None:
            from .services import ensure_studio_has_room

            ensure_studio_has_room(self.studio_id, joining_teacher_id=self.pk)
