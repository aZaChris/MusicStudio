"""Append-only record of sensitive actions (constitution X, ADR-031).

Entries hold identifiers, never names, emails, passwords, codes, tokens or card data, so
the log itself does not become a second copy of personal data.
"""

from typing import Any

from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    class Action(models.TextChoices):
        REGISTRATION = "registration"
        EMAIL_CONFIRM = "email.confirm"
        LOGIN_SUCCESS = "login.success"
        LOGIN_FAILURE = "login.failure"
        LOGIN_LOCKED = "login.locked"
        PASSWORD_RESET = "password.reset"  # noqa: S105 - an action name, not a secret
        PASSWORD_CHANGE = "password.change"  # noqa: S105
        MFA_ENABLE = "mfa.enable"
        MFA_DISABLE = "mfa.disable"
        MFA_RECOVERY_USED = "mfa.recovery_used"
        MFA_RESET_BY_OPERATOR = "mfa.reset_by_operator"
        ACCOUNT_UNLOCK_BY_OPERATOR = "account.unlock_by_operator"
        INVITATION_SEND = "invitation.send"
        INVITATION_ACCEPT = "invitation.accept"
        INVITATION_REVOKE = "invitation.revoke"
        ROLE_CHANGE = "role.change"
        CONSENT_GIVE = "consent.give"
        CONSENT_WITHDRAW = "consent.withdraw"
        PRIVACY_EXPORT = "privacy.export"
        PRIVACY_ERASE = "privacy.erase"
        PAYMENT_RECORD = "payment.record"

    class Outcome(models.TextChoices):
        SUCCESS = "success"
        FAILURE = "failure"
        DENIED = "denied"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=40, choices=Action.choices)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.SUCCESS)
    studio = models.ForeignKey(
        "studios.Studio", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    target_type = models.CharField(max_length=40, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["studio", "-created_at"], name="audit_studio_recent")]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.outcome}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk is not None:
            raise PermissionError("Audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise PermissionError("Audit entries are deleted only by the retention job.")
