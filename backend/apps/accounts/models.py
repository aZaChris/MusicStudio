from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDIO_OWNER = "studio_owner", "Studio owner"
        PARENT = "parent", "Parent"

    class Language(models.TextChoices):
        EN = "en", "English"
        IT = "it", "Italiano"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    preferred_language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.EN
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email
