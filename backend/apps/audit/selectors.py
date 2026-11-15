"""Letture del registro delle azioni, riservate al titolare dello studio (ADR-031)."""

from datetime import datetime

from django.db.models import Q, QuerySet

from apps.common.tenancy import TenantContext

from .models import AuditEntry


def entries_for_owner(
    ctx: TenantContext,
    *,
    action: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> QuerySet[AuditEntry]:
    """Voci dello studio del titolare, dalla più recente.

    Le voci registrate con uno studio le mostra quello studio. Gli accessi non hanno uno studio
    (la persona può appartenerne a più d'uno), quindi si mostrano solo per gli insegnanti dello
    studio: il titolare vede chi del suo team accede, non cosa fanno i genitori altrove.
    """
    # Solo il titolare legge il registro: per gli altri ruoli il risultato è vuoto, non un errore.
    if not ctx.is_owner:
        return AuditEntry.objects.none()
    qs = AuditEntry.objects.select_related("actor").filter(
        Q(studio_id=ctx.studio_id) | Q(studio__isnull=True, actor__teacher__studio_id=ctx.studio_id)
    )
    # Filtri opzionali, già validati dal serializer della view.
    if action:
        qs = qs.filter(action=action)
    if since:
        qs = qs.filter(created_at__gte=since)
    if until:
        qs = qs.filter(created_at__lte=until)
    return qs.order_by("-created_at", "-id")
