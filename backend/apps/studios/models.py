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
    studio = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name="teachers"
    )
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.is_owner and self.studio_id is None:
            raise ValidationError("A studio owner must belong to a studio.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.user.email
