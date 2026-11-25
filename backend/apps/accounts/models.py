"""Utente, inviti, dispositivo MFA e codici di recupero.

Spiegazione: docs/learning/concetti/account-e-token-monouso.md e docs/learning/concetti/mfa-totp.md.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.fields import EncryptedTextField


class User(AbstractUser):
    # Un solo modello utente per tutti i ruoli; il ruolo decide che profilo c'è dietro
    # (insegnante, genitore, studente). Si accede con l'email, non con lo username.
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        STUDIO_OWNER = "studio_owner", "Studio owner"
        PARENT = "parent", "Parent"
        # Solo studenti adulti, in sola lettura, solo i propri dati (fase 7, constitution X).
        STUDENT = "student", "Student"

    class Language(models.TextChoices):
        EN = "en", "English"
        IT = "it", "Italiano"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    preferred_language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.EN
    )

    # Gli account registrati da soli restano inutilizzabili finché l'indirizzo non è confermato
    # (fase 7). db_default: le righe inserite da codice vecchio (o da vecchie migrazioni) hanno
    # comunque un valore.
    email_verified = models.BooleanField(default=False, db_default=False)
    # Blocco per singolo account (ADR-028 / research R4): 5 errori bloccano per 15 min x 2^livello.
    failed_logins = models.PositiveIntegerField(default=0, db_default=0)
    lock_level = models.PositiveSmallIntegerField(default=0, db_default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email

    @property
    def is_operator(self) -> bool:
        # Operatore = chi gestisce la piattaforma, non uno studio: attivo, staff e senza ruolo
        # di studio (gli account di `createsuperuser` hanno ruolo vuoto). Solo lui entra
        # nell'admin (ADR-041); un ruolo di studio non passa nemmeno con is_staff forzato.
        return self.is_active and self.is_staff and not self.role


class Invitation(models.Model):
    """Un utente registrato invita qualcuno nel proprio studio (US3, research R2).

    Si salva solo lo SHA-256 del token: una fuga del database non rivela link utilizzabili.
    "Scaduto" non è uno stato salvato: è `expires_at` nel passato.
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
            # Un solo invito attivo per persona e ruolo in uno studio; uno nuovo sostituisce quello
            # vecchio (lo fa invitations.create_invitation).
            models.UniqueConstraint(
                fields=["studio", "email", "role"],
                condition=models.Q(status="pending"),
                name="one_pending_invitation",
            )
        ]

    def __str__(self) -> str:
        return f"{self.role} invitation #{self.pk}"


class MfaDevice(models.Model):
    """L'app di autenticazione di un titolare o insegnante (ADR-029). Attiva dopo la conferma."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="mfa_device")
    secret = EncryptedTextField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # Passo TOTP dell'ultimo codice accettato: un codice si usa una volta sola (anti-replay).
    last_used_step = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return f"MFA device of user #{self.user_id}"


class RecoveryCode(models.Model):
    """Codice monouso per quando si perde il telefono. Si salva solo il suo SHA-256: il codice è
    casuale (50 bit), quindi un hash veloce basta e controllarne dieci costa poco."""

    device = models.ForeignKey(MfaDevice, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Recovery code #{self.pk}"
