"""Scrittura delle voci del registro. La chiamano i service che compiono azioni sensibili (ADR-031).

Il registro nasce dai service e non da un middleware: solo lì si sa cosa è successo davvero.
"""

from typing import Any

from django.db.models import Model

from apps.common.logging import request_id_var

from .models import AuditEntry

Action = AuditEntry.Action
Outcome = AuditEntry.Outcome

# Tipi ammessi nei metadata: fatti brevi e non personali (ruolo, livello di blocco, conteggi).
# Tutto il resto (liste, oggetti annidati) viene scartato in silenzio.
_SAFE_METADATA_TYPES = (bool, int, str)


def record(
    action: str,
    *,
    actor: Any = None,
    target: Model | None = None,
    studio_id: int | None = None,
    outcome: str = Outcome.SUCCESS,
    metadata: dict[str, Any] | None = None,
) -> AuditEntry:
    """Aggiunge una voce. `actor` può essere anonimo (None) per accessi falliti e job."""
    clean = {k: v for k, v in (metadata or {}).items() if isinstance(v, _SAFE_METADATA_TYPES)}
    # L'id della richiesta collega la voce ai log JSON; "-" vuol dire fuori da una richiesta.
    request_id = request_id_var.get()
    return AuditEntry.objects.create(
        action=action,
        outcome=outcome,
        actor=actor if getattr(actor, "pk", None) else None,
        studio_id=studio_id,
        target_type=(target._meta.model_name or "") if target is not None else "",
        target_id=target.pk if target is not None else None,
        request_id="" if request_id == "-" else request_id,
        metadata=clean,
    )


def purge_older_than(cutoff: Any) -> int:
    """Conservazione (12 mesi): l'unico percorso che cancella voci, e solo in blocco."""
    deleted, _ = AuditEntry.objects.filter(created_at__lt=cutoff).delete()
    return deleted
