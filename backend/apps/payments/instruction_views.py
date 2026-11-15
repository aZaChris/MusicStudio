"""Endpoint delle istruzioni di pagamento: lo studio le gestisce, i genitori le leggono.

Le view sono sottili; i docstring finiscono in openapi.yaml (contratto in inglese), quindi qui
si usano commenti `#`. Lo studio viene sempre dal contesto di chi chiama, mai da un id nella
richiesta: non c'è un id da forzare (constitution I). IBAN e intestatario non compaiono mai nei
log né nei report di errore (vedi common/sentry.py).
"""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsFamilyRole, IsStudioOwner, IsTeacherOrOwnerRole
from apps.common.tenancy import get_tenant
from apps.studios.models import Studio

from . import selectors, services
from .models import PaymentInstructions
from .serializers import OpenInstructionsSerializer, PaymentInstructionsSerializer

# La frase che accompagna le istruzioni (FR-021). L'app web la mostra tradotta; questa versione
# in inglese è per gli altri client (la app mobile) che leggono il contratto.
NOTICE = "Payment happens outside MusicStudio and is not verified by it."


def _empty() -> dict[str, Any]:
    return {
        "account_holder": "",
        "iban": "",
        "bank_name": "",
        "note": "",
        "links": [],
        "updated_at": None,
    }


def _present(instructions: PaymentInstructions | None) -> dict[str, Any]:
    if instructions is None:
        return _empty()
    return {
        "account_holder": instructions.account_holder,
        "iban": instructions.iban,
        "bank_name": instructions.bank_name,
        "note": instructions.note,
        "links": instructions.links,
        "updated_at": instructions.updated_at,
    }


class PaymentInstructionsView(APIView):
    # GET: insegnanti e titolari leggono le istruzioni del proprio studio. PUT: solo il
    # titolare le sostituisce (un insegnante riceve 403). Senza istruzioni salvate la risposta
    # ha tutti i campi vuoti. Un corpo tutto vuoto le cancella.
    def get_permissions(self) -> list[Any]:
        return [IsStudioOwner() if self.request.method == "PUT" else IsTeacherOrOwnerRole()]

    @extend_schema(responses={200: PaymentInstructionsSerializer})
    def get(self, request: Request) -> Response:
        ctx = get_tenant(request)
        return Response(
            PaymentInstructionsSerializer(_present(selectors.instructions_for_studio(ctx))).data
        )

    @extend_schema(
        request=PaymentInstructionsSerializer, responses={200: PaymentInstructionsSerializer}
    )
    def put(self, request: Request) -> Response:
        ctx = get_tenant(request)
        if ctx.studio_id is None:
            raise NotFound("No studio is linked to this account.")
        body = PaymentInstructionsSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        studio = Studio.objects.get(pk=ctx.studio_id)
        saved = services.save_instructions(studio, actor=request.user, data=body.validated_data)
        return Response(PaymentInstructionsSerializer(_present(saved)).data)


class OpenInstructionsView(APIView):
    # GET per genitori e studenti adulti: le istruzioni degli studi in cui hanno almeno un
    # pacchetto ancora da pagare. Il portale le abbina ai pacchetti tramite lo studio dello
    # studente. Lista vuota se non c'è nulla da pagare o lo studio non ha istruzioni.
    permission_classes = [IsFamilyRole]

    @extend_schema(responses={200: OpenInstructionsSerializer(many=True)})
    def get(self, request: Request) -> Response:
        rows = selectors.instructions_for_open_packages(get_tenant(request))
        data = [
            {
                **_present(row),
                "studio_id": row.studio_id,
                "studio_name": row.studio.name,
                "student_ids": student_ids,
                "notice": NOTICE,
            }
            for row, student_ids in rows
        ]
        return Response(OpenInstructionsSerializer(data, many=True).data)  # type: ignore[arg-type]
