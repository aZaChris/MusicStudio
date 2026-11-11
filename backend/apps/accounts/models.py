from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDIO_OWNER = "studio_owner", "Studio owner"
        PARENT = "parent", "Parent"
        # Adult students only, read-only, their own data (phase 7, constitution X).
        STUDENT = "student", "Student"

    class Language(models.TextChoices):
        EN = "en", "English"
        IT = "it", "Italiano"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    preferred_language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.EN
    )

    # Self-registered accounts stay unusable until the address is confirmed (phase 7).
    # db_default: rows inserted by older code (or old migration states) still get a value.
    email_verified = models.BooleanField(default=False, db_default=False)
    # Per-account lockout (ADR-028 / research R4): 5 failures lock for 15 min x 2^level.
    failed_logins = models.PositiveIntegerField(default=0, db_default=0)
    lock_level = models.PositiveSmallIntegerField(default=0, db_default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email
