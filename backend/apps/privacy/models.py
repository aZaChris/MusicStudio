"""Consent, the legal basis we record for minors' data (constitution X, ADR-032)."""

from django.db import models


class ConsentRecord(models.Model):
    """A parent agreed to the privacy notice `notice_version` for these children."""

    parent = models.ForeignKey(
        "students.ParentAccount",
        null=True,
        on_delete=models.SET_NULL,
        related_name="consents",
    )
    students = models.ManyToManyField("students.Student", related_name="consents")
    notice_version = models.CharField(max_length=20)
    given_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-given_at", "-id"]

    def __str__(self) -> str:
        return f"consent #{self.pk} ({self.notice_version})"
