"""Consenso: la base giuridica che registriamo per i dati dei minori (constitution X, ADR-032).

Spiegazione: docs/learning/concetti/gdpr-per-sviluppatori.md.
"""

from django.db import models


class ConsentRecord(models.Model):
    """Un genitore ha accettato l'informativa `notice_version` per questi figli.

    Si salva la *versione* dell'informativa, non il testo: se cambia, si sa chi ha accettato quale.
    """

    # SET_NULL: se l'account genitore sparisce il consenso resta come prova, senza collegamento.
    parent = models.ForeignKey(
        "students.ParentAccount",
        null=True,
        on_delete=models.SET_NULL,
        related_name="consents",
    )
    students = models.ManyToManyField("students.Student", related_name="consents")
    notice_version = models.CharField(max_length=20)
    given_at = models.DateTimeField(auto_now_add=True)
    # Valorizzato quando il genitore ritira il consenso (privacy.services.withdraw_consent).
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-given_at", "-id"]

    def __str__(self) -> str:
        return f"consent #{self.pk} ({self.notice_version})"
