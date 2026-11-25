"""Inventario dell'export GDPR: per ogni modello del progetto, esportato o escluso e perché.

Un test (tests/test_export_inventory.py) elenca tutti i modelli di `apps.*` e fallisce su quelli
che mancano qui; un secondo controlla che ogni chiave "exported" esista davvero nell'export.
Così un modello nuovo con dati personali non può restare fuori dall'export senza che qualcuno
lo decida per iscritto (ADR-042, constitution X).
Spiegazione: docs/learning/concetti/gdpr-per-sviluppatori.md.
"""

from typing import Literal

Kind = Literal["exported", "excluded"]

# "exported": la chiave di primo livello dell'export che contiene i dati del modello.
# "excluded": il motivo, in una frase.
INVENTORY: dict[str, tuple[Kind, str]] = {
    "accounts.User": ("exported", "account"),
    "accounts.Invitation": ("exported", "invitations"),
    "accounts.MfaDevice": ("exported", "account"),  # solo "attiva sì/no", mai il segreto
    "accounts.RecoveryCode": ("excluded", "Hashes of one-time credentials, not personal data."),
    "audit.AuditEntry": ("exported", "activity"),
    "lessons.Lesson": ("exported", "children"),
    "notifications.ReminderDelivery": ("exported", "reminders"),
    "packages.Package": ("exported", "children"),
    "payments.Payment": ("exported", "children"),
    "payments.Receipt": ("exported", "children"),  # il numero, sul pagamento (ADR-035)
    "payments.CheckoutSession": ("exported", "online_checkouts"),
    "payments.PaymentDispute": (
        "excluded",
        "A dispute already shows as a reversal row of the family's payment (ADR-038).",
    ),
    "payments.WebhookEvent": (
        "excluded",
        "Technical provider events, scrubbed of personal data before saving (ADR-039).",
    ),
    "payments.StudioPaymentAccount": ("exported", "studio"),
    "payments.PaymentInstructions": ("exported", "studio"),
    "privacy.ConsentRecord": ("exported", "consents"),
    "students.Student": ("exported", "children"),
    "students.ParentAccount": ("exported", "account"),
    "students.ParentStudentLink": ("exported", "children"),
    "studios.Studio": ("exported", "children"),  # il nome dello studio di ogni figlio
    "studios.Teacher": (
        "excluded",
        "The teacher's own record, not the family's; the studio name is exported.",
    ),
}
