"""Read queries for the audit log (studio owner only)."""

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
    """Entries of the owner's studio, newest first.

    Entries recorded with a studio are shown by that studio. Sign-in events carry no studio
    (the person may belong to several), so those are shown for the studio's own teachers only:
    an owner sees who in their team signs in, not what parents do elsewhere.
    """
    if not ctx.is_owner:
        return AuditEntry.objects.none()
    qs = AuditEntry.objects.select_related("actor").filter(
        Q(studio_id=ctx.studio_id) | Q(studio__isnull=True, actor__teacher__studio_id=ctx.studio_id)
    )
    if action:
        qs = qs.filter(action=action)
    if since:
        qs = qs.filter(created_at__gte=since)
    if until:
        qs = qs.filter(created_at__lte=until)
    return qs.order_by("-created_at", "-id")
