"""Endpoint del registro di cassa: riepilogo di un periodo ed esportazioni CSV e PDF (fase 8).

Solo insegnanti e titolari: genitori e studenti adulti non vedono il registro (FR-013).
Le view sono sottili; i docstring finiscono in openapi.yaml (contratto in inglese), quindi qui
si usano commenti `#`. Spiegazione: docs/learning/concetti/registro-di-cassa.md.
"""

import datetime
from typing import Any

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.common.permissions import IsTeacherOrOwnerRole
from apps.common.tenancy import get_tenant
from apps.common.throttling import ScopedRateThrottle
from apps.studios.models import Studio

from . import selectors
from .exports import write_register_csv
from .pdf import register_pdf
from .serializers import ExportQuerySerializer, PeriodQuerySerializer, RegisterSummarySerializer

# Un'esportazione copre al massimo un anno (FR-017): oltre, 400 `period_too_long`.
MAX_EXPORT_DAYS = 366

_PERIOD_PARAMS = [
    OpenApiParameter("date_from", datetime.date, description="First day, YYYY-MM-DD, inclusive."),
    OpenApiParameter("date_to", datetime.date, description="Last day, YYYY-MM-DD, inclusive."),
]


class RegisterSummaryView(APIView):
    # GET /payments/register/summary/: incassato, stornato e netto del periodo, in totale e per
    # metodo. Senza parametri: il mese corrente. Un periodo vuoto dà zeri, non un errore.
    permission_classes = [IsTeacherOrOwnerRole]

    @extend_schema(
        parameters=_PERIOD_PARAMS,
        responses={200: RegisterSummarySerializer},
    )
    def get(self, request: Request) -> Response:
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        start, end = selectors.current_month()
        date_from = query.validated_data.get("date_from", start)
        date_to = query.validated_data.get("date_to", end)
        selectors.ensure_period(date_from, date_to)
        summary = selectors.register_summary(get_tenant(request), date_from, date_to)
        return Response(RegisterSummarySerializer(summary).data)


class _ExportView(APIView):
    # Base delle due esportazioni: periodo obbligatorio e al massimo di un anno, limite di
    # frequenza dedicato (scope `register_export`), voce nel registro delle azioni con il
    # periodo e il numero di righe, mai il contenuto.
    permission_classes = [IsTeacherOrOwnerRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register_export"
    file_format = ""

    def _period(self, request: Request) -> tuple[datetime.date, datetime.date]:
        query = ExportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        date_from, date_to = query.validated_data["date_from"], query.validated_data["date_to"]
        selectors.ensure_period(date_from, date_to, max_days=MAX_EXPORT_DAYS)
        return date_from, date_to

    def _audit(self, request: Request, date_from: Any, date_to: Any, rows: int) -> None:
        audit.record(
            audit.Action.REGISTER_EXPORT,
            actor=request.user,
            studio_id=get_tenant(request).studio_id,
            metadata={
                "format": self.file_format,
                "from": date_from.isoformat(),
                "to": date_to.isoformat(),
                "rows": rows,
            },
        )

    def _attachment(
        self, data: bytes, content_type: str, date_from: Any, date_to: Any
    ) -> HttpResponse:
        response = HttpResponse(data, content_type=content_type)
        name = f"register-{date_from.isoformat()}_{date_to.isoformat()}.{self.file_format}"
        response["Content-Disposition"] = f'attachment; filename="{name}"'
        return response


class RegisterCsvExportView(_ExportView):
    # GET /payments/register/export/csv/: una riga per pagamento (anche in sospeso e scaduti).
    file_format = "csv"

    @extend_schema(
        parameters=_PERIOD_PARAMS,
        responses={200: OpenApiResponse(description="CSV attachment, one row per entry")},
    )
    def get(self, request: Request) -> HttpResponse:
        date_from, date_to = self._period(request)
        rows = selectors.register_rows(get_tenant(request), date_from, date_to)
        self._audit(request, date_from, date_to, len(rows))
        return self._attachment(
            write_register_csv(rows), "text/csv; charset=utf-8", date_from, date_to
        )


class RegisterPdfExportView(_ExportView):
    # GET /payments/register/export/pdf/: studio, periodo, totali per metodo, data di produzione.
    file_format = "pdf"

    @extend_schema(
        parameters=_PERIOD_PARAMS,
        responses={200: OpenApiResponse(description="PDF attachment with the period totals")},
    )
    def get(self, request: Request) -> HttpResponse:
        date_from, date_to = self._period(request)
        ctx = get_tenant(request)
        if ctx.studio_id is None:  # un account con ruolo ma senza profilo: nessuno studio
            raise NotFound("No studio is linked to this account.")
        summary = selectors.register_summary(ctx, date_from, date_to)
        studio_name = Studio.objects.values_list("name", flat=True).get(pk=ctx.studio_id)
        language = getattr(request.user, "preferred_language", "en")
        pdf = register_pdf(
            studio_name=studio_name,
            summary=summary,
            produced_on=datetime.date.today(),
            language=language,
        )
        self._audit(request, date_from, date_to, sum(summary["counts"].values()))
        return self._attachment(pdf, "application/pdf", date_from, date_to)
