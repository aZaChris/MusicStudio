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


class Invitation(models.Model):
    """A signed-up user invites someone into their studio (US3, research R2).

    Only the SHA-256 of the token is stored: a database leak does not leak usable links.
    "Expired" is not stored; it is `expires_at` in the past.
    """

    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        PARENT = "parent", "Parent"
        STUDENT = "student", "Student"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"

    studio = models.ForeignKey("studios.Studio", on_delete=models.CASCADE, related_name="+")
    invited_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="invitations_sent"
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Role.choices)
    students = models.ManyToManyField("students.Student", blank=True, related_name="+")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    accepted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # One live invitation per person and role in a studio; a new one replaces it.
            models.UniqueConstraint(
                fields=["studio", "email", "role"],
                condition=models.Q(status="pending"),
                name="one_pending_invitation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.role} invitation #{self.pk}"
