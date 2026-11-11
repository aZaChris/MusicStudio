from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView

from apps.common.permissions import IsStudioOwner
from apps.common.tenancy import get_tenant

from .models import AuditEntry
from .selectors import entries_for_owner
from .serializers import AuditEntrySerializer, AuditFilterSerializer


class AuditListView(ListAPIView[AuditEntry]):
    """Who did what in the owner's studio, newest first."""

    serializer_class = AuditEntrySerializer
    permission_classes = [IsStudioOwner]

    @extend_schema(
        parameters=[
            OpenApiParameter("action", str, enum=[a.value for a in AuditEntry.Action]),
            OpenApiParameter("since", str, description="ISO 8601 date-time"),
            OpenApiParameter("until", str, description="ISO 8601 date-time"),
        ]
    )
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[AuditEntry]:
        filters = AuditFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return entries_for_owner(get_tenant(self.request), **filters.validated_data)
