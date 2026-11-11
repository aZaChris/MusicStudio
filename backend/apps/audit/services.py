"""Write audit entries. Called by the services that perform sensitive actions (ADR-031)."""

from typing import Any

from django.db.models import Model

from apps.common.logging import request_id_var

from .models import AuditEntry

Action = AuditEntry.Action
Outcome = AuditEntry.Outcome

# Values allowed in metadata: short, non-personal facts (role, lock level, counts).
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
    """Append one entry. `actor` may be anonymous (None) for failed sign-ins and jobs."""
    clean = {k: v for k, v in (metadata or {}).items() if isinstance(v, _SAFE_METADATA_TYPES)}
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
    """Retention (12 months): the only path that deletes entries, in bulk."""
    deleted, _ = AuditEntry.objects.filter(created_at__lt=cutoff).delete()
    return deleted
