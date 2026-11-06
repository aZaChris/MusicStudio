from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Studio(models.Model):
    name = models.CharField(max_length=200)
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="teacher"
    )
    # Every teacher belongs to exactly one studio, the tenant (ADR-010). A solo teacher owns
    # a personal studio of one. PROTECT: deleting a studio must not silently orphan data.
    studio = models.ForeignKey(Studio, on_delete=models.PROTECT, related_name="teachers")
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Was a save() override calling clean(); the database now guarantees it for
            # every write path (bulk updates and raw SQL included).
            models.CheckConstraint(
                condition=models.Q(is_owner=False) | models.Q(studio__isnull=False),
                name="teacher_owner_has_studio",
            )
        ]

    def __str__(self) -> str:
        return self.user.email

    def clean(self) -> None:
        if self.is_owner and self.studio_id is None:
            raise ValidationError("A studio owner must belong to a studio.")
        if self.studio_id is not None:
            from .services import ensure_studio_has_room

            ensure_studio_has_room(self.studio_id, joining_teacher_id=self.pk)
