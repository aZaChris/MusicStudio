"""Endpoint della privacy: esportazione, cancellazione dell'account e consensi.

Le view sono sottili. I docstring finiscono in openapi.yaml (contratto in inglese): qui si
usano commenti `#`. Spiegazione: docs/learning/concetti/gdpr-per-sviluppatori.md.
"""

import json
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit import services as audit
from apps.common.throttling import ScopedRateThrottle

from . import selectors, services
from .models import ConsentRecord
from .serializers import AcceptedSerializer, ConsentSerializer, PasswordSerializer


class _Role(BasePermission):
    # Permesso base: l'utente è autenticato e ha uno dei ruoli elencati in `roles`.
    roles: tuple[str, ...] = ()

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.roles)


class IsFamily(_Role):
    """Genitori e studenti adulti: le persone di cui l'esportazione riguarda i dati."""

    roles = (User.Role.PARENT, User.Role.STUDENT)


class CanErase(_Role):
    # Anche il titolare può chiudere l'account, ma solo se lo studio non ha più studenti
    # (privacy.services.StudioNotEmpty).
    roles = (User.Role.PARENT, User.Role.STUDENT, User.Role.STUDIO_OWNER)


class ExportView(APIView):
    # GET: scarica un JSON con tutti i dati dell'account. Limitata da throttle (scope `privacy`).
    permission_classes = [IsAuthenticated, IsFamily]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "privacy"

    @extend_schema(responses={200: OpenApiResponse(description="JSON attachment")})
    def get(self, request: Request) -> HttpResponse:
        user: User = request.user  # type: ignore[assignment]
        payload = json.dumps(selectors.build_export(user), cls=DjangoJSONEncoder, indent=2)
        # Anche l'esportazione finisce nel registro delle azioni (ADR-031).
        audit.record(audit.Action.PRIVACY_EXPORT, actor=user, target=user)
        response = HttpResponse(payload, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="musicstudio-export.json"'
        return response


class EraseView(APIView):
    # POST: cancella (anonimizza) l'account, previa conferma con la password. Risponde 202.
    permission_classes = [IsAuthenticated, CanErase]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "privacy"

    @extend_schema(request=PasswordSerializer, responses={202: AcceptedSerializer})
    def post(self, request: Request) -> Response:
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.erase_account(request.user, serializer.validated_data["password"])  # type: ignore[arg-type]
        return Response({"detail": "erased"}, status=status.HTTP_202_ACCEPTED)


class ConsentListView(APIView):
    # GET: i consensi dati dal genitore che chiama.
    permission_classes = [IsAuthenticated, IsFamily]

    @extend_schema(responses={200: ConsentSerializer(many=True)})
    def get(self, request: Request) -> Response:
        records = ConsentRecord.objects.filter(
            parent__user=request.user  # type: ignore[misc]
        ).prefetch_related("students")
        return Response(ConsentSerializer(records, many=True).data)


class ConsentWithdrawView(APIView):
    # POST: ritira un consenso (con la password). Il genitore viene scollegato dai figli.
    permission_classes = [IsAuthenticated, IsFamily]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "privacy"

    @extend_schema(request=PasswordSerializer, responses={202: AcceptedSerializer})
    def post(self, request: Request, pk: int) -> Response:
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.withdraw_consent(request.user, pk, serializer.validated_data["password"])  # type: ignore[arg-type]
        return Response({"detail": "withdrawn"}, status=status.HTTP_202_ACCEPTED)
