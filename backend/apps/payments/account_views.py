"""Endpoint del conto di pagamento dello studio (fase 9, ADR-037).

Le view sono sottili; i docstring finiscono in openapi.yaml (contratto in inglese), quindi qui si
usano commenti `#`. Lo studio viene sempre dal contesto di chi chiama, mai da un id nella richiesta:
non c'è un id da forzare (constitution I). Il titolare scrive, gli insegnanti leggono; genitori e
studenti non hanno accesso. Con l'interruttore spento ogni rotta risponde 404.
"""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.permissions import IsStudioOwner, IsTeacherOrOwnerRole
from apps.common.tenancy import get_tenant
from apps.studios.models import Studio

from . import selectors, services
from .models import StudioPaymentAccount
from .serializers import OnboardingLinkSerializer, PaymentAccountSerializer

# Pagina di Stripe per vedere saldi, bonifici e rimborsi del proprio conto (siamo in modalità test).
DASHBOARD_URL = "https://dashboard.stripe.com/test/dashboard"


def _present(account: StudioPaymentAccount | None) -> dict[str, Any]:
    if account is None:
        return {
            "state": "not_started",
            "can_accept_online": False,
            "test_mode": True,
            "dashboard_url": None,
            "state_changed_at": None,
            "needs_attention": [],
        }
    return {
        "state": account.state,
        "can_accept_online": account.can_accept_online,
        "test_mode": True,
        "dashboard_url": DASHBOARD_URL,
        "state_changed_at": account.state_changed_at,
        "needs_attention": selectors.attention_items(account),
    }


def _studio(request: Request) -> Studio:
    ctx = get_tenant(request)
    if ctx.studio_id is None:
        raise NotFound("No studio is linked to this account.")
    return Studio.objects.get(pk=ctx.studio_id)


class PaymentAccountView(APIView):
    # GET: titolare e insegnanti leggono lo stato del conto del proprio studio. Solo database,
    # nessuna chiamata a Stripe.
    permission_classes = [IsTeacherOrOwnerRole]

    @extend_schema(responses={200: PaymentAccountSerializer})
    def get(self, request: Request) -> Response:
        services.require_online_payments()
        account = selectors.payment_account_for(get_tenant(request))
        return Response(PaymentAccountSerializer(_present(account)).data)


class _OwnerActionView(APIView):
    # Base delle tre azioni del titolare: solo lui, con un limite di frequenza (parlano con Stripe).
    permission_classes = [IsStudioOwner]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment_account"


class OnboardingView(_OwnerActionView):
    # POST: crea il conto dello studio se manca e ritorna l'indirizzo della pagina di Stripe dove
    # il titolare lo completa. Due richieste insieme creano un solo conto.
    @extend_schema(request=None, responses={200: OnboardingLinkSerializer})
    def post(self, request: Request) -> Response:
        link = services.start_onboarding(_studio(request), actor=request.user)
        return Response(
            OnboardingLinkSerializer({"url": link.url, "expires_at": link.expires_at}).data
        )


class RefreshView(_OwnerActionView):
    # POST: rilegge il conto da Stripe (il portale lo chiama quando il titolare torna dalla pagina
    # di Stripe) e ritorna lo stato aggiornato.
    @extend_schema(request=None, responses={200: PaymentAccountSerializer})
    def post(self, request: Request) -> Response:
        account = services.refresh_account(_studio(request))
        return Response(PaymentAccountSerializer(_present(account)).data)


class RestartView(_OwnerActionView):
    # POST: toglie il collegamento di un conto scollegato per poter ricominciare. 409 se il conto
    # non è scollegato.
    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        services.restart_account(_studio(request), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
