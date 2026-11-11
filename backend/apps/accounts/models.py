from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.fields import EncryptedTextField


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


class MfaDevice(models.Model):
    """The authenticator app of an owner or teacher (ADR-029). Active once confirmed."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mfa_device")
    secret = EncryptedTextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # TOTP step of the last accepted code: a code can be used once (anti-replay).
    last_used_step = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return f"MFA device of user #{self.user_id}"


class RecoveryCode(models.Model):
    """Single-use code for when the phone is lost. Only its SHA-256 is stored: the code is
    random (50 bits), so a fast hash is enough and checking ten of them stays cheap."""

    device = models.ForeignKey(MfaDevice, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Recovery code #{self.pk}"
