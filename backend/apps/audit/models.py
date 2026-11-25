"""Registro append-only delle azioni sensibili (constitution X, ADR-031).

Le voci contengono identificativi, mai nomi, email, password, codici, token o dati di carta:
il registro non deve diventare una seconda copia dei dati personali.
Spiegazione: docs/learning/concetti/audit-log.md.
"""

from typing import Any

from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    # Una riga = un'azione sensibile: chi (actor), che cosa (action), com'è andata (outcome),
    # su quale oggetto (target) e in quale studio. Si scrive solo da audit.services.record.
    class Action(models.TextChoices):
        # Elenco chiuso delle azioni registrate. Una nuova azione richiede una migrazione dei
        # `choices` e va aggiunta anche ai filtri dell'API (si leggono da qui).
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
        # Fase 8 (registro di cassa, istruzioni di pagamento, ricevute).
        PAYMENT_REVERSE = "payment.reverse"
        PAYMENT_DELETE = "payment.delete"
        REGISTER_EXPORT = "register.export"
        INSTRUCTIONS_CHANGE = "instructions.change"
        RECEIPT_ISSUE = "receipt.issue"
        # Fase 9 (pagamenti online sul conto dello studio): conto, rimborsi e contestazioni.
        PAYMENT_ACCOUNT_START = "payment_account.start"
        PAYMENT_ACCOUNT_STATE = "payment_account.state"
        PAYMENT_REFUND = "payment.refund"
        PAYMENT_DISPUTE = "payment.dispute"
        # Fase 10 (admin solo per operatori): accessi, modifiche e cancellazioni dall'admin.
        ADMIN_LOGIN = "admin.login"
        ADMIN_CHANGE = "admin.change"
        ADMIN_DELETE = "admin.delete"

    class Outcome(models.TextChoices):
        # success = riuscita; failure = tentata e fallita; denied = negata dai permessi.
        SUCCESS = "success"
        FAILURE = "failure"
        DENIED = "denied"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # SET_NULL su actor e studio: se l'utente o lo studio vengono cancellati la voce resta,
    # ma senza più il collegamento.
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
    # Lo stesso id che compare nei log JSON: da una voce si risale alla richiesta (ADR-019).
    request_id = models.CharField(max_length=64, blank=True)
    # Solo fatti brevi e non personali; il filtro è in audit.services.record.
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        # La lettura tipica è "le voci recenti di uno studio": l'indice la serve senza ordinare.
        indexes = [models.Index(fields=["studio", "-created_at"], name="audit_studio_recent")]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.outcome}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Append-only: si può solo inserire. Una voce già salvata non si riscrive.
        if self.pk is not None:
            raise PermissionError("Audit entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        # Si cancella solo in blocco, dal job di conservazione (audit.services.purge_older_than).
        raise PermissionError("Audit entries are deleted only by the retention job.")
