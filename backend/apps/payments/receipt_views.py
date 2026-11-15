"""Endpoint delle ricevute non fiscali: emissione, elenco e PDF (fase 8, ADR-035).

Le view sono sottili. I docstring finiscono in openapi.yaml (contratto in inglese), quindi qui
si usano commenti `#`. Chi emette: insegnanti e titolari, nel proprio ambito. Chi scarica: anche
genitori e studenti adulti, solo le ricevute dei propri studenti. Un id fuori ambito dà 404.
"""

import django_filters
from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsTeacherOrOwnerRole
from apps.common.tenancy import get_tenant
from apps.common.throttling import ScopedRateThrottle

from . import pdf, selectors, services
from .models import Receipt
from .serializers import ReceiptRequestSerializer, ReceiptSerializer


class IssueReceiptView(APIView):
    # POST /payments/{id}/receipt/: emette la ricevuta (201) o restituisce quella già emessa
    # (200, stesso numero). Il pagamento si cerca nell'ambito di chi chiama: se non è suo, 404.
    # Un pagamento in sospeso, scaduto o di storno dà 409.
    permission_classes = [IsTeacherOrOwnerRole]

    @extend_schema(
        request=ReceiptRequestSerializer, responses={201: ReceiptSerializer, 200: ReceiptSerializer}
    )
    def post(self, request: Request, pk: int) -> Response:
        ctx = get_tenant(request)
        payment = selectors.payments_for(ctx).filter(pk=pk).first()
        if payment is None:
            raise Http404
        body = ReceiptRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        language = body.validated_data.get("language") or (
            getattr(request.user, "preferred_language", None) or "it"
        )
        receipt, created = services.issue_receipt(payment, language=language, actor=request.user)
        # La ricevuta appena creata non ha il pagamento in cache: si rilegge dal selector, con
        # gli stessi dati che vedrebbe l'elenco.
        fresh = selectors.receipts_for(ctx).get(pk=receipt.pk)
        return Response(
            ReceiptSerializer(fresh).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ReceiptFilter(django_filters.FilterSet):
    student = django_filters.NumberFilter(field_name="payment__student")

    class Meta:
        model = Receipt
        fields = ["student"]


class ReceiptListView(ListAPIView[Receipt]):
    # GET /receipts/?student=: le ricevute emesse che chi chiama può vedere. Per genitori e
    # studenti adulti solo quelle dei propri studenti (RECEIPT_PATHS in common/scoping.py).
    permission_classes = [IsAuthenticated]
    serializer_class = ReceiptSerializer
    filterset_class = ReceiptFilter

    def get_queryset(self):  # type: ignore[no-untyped-def]
        return selectors.receipts_for(get_tenant(self.request))


class ReceiptPdfView(APIView):
    # GET /receipts/{id}/pdf/: il PDF, generato dai dati attuali con lo stesso numero. Esce con
    # il segno "annullata" se il pagamento è stato stornato. Limite di frequenza dedicato.
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register_export"

    @extend_schema(responses={200: OpenApiResponse(description="PDF attachment")})
    def get(self, request: Request, pk: int) -> HttpResponse:
        receipt = selectors.receipts_for(get_tenant(request)).filter(pk=pk).first()
        if receipt is None:
            raise Http404
        payment = receipt.payment
        data = pdf.receipt_pdf(
            studio_name=receipt.studio.name,
            student_name=payment.student.full_name,
            amount=payment.amount,
            day=payment.date,
            method=payment.method,
            number=receipt.number,
            language=receipt.language,
            cancelled=selectors.is_reversed(payment),
        )
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="receipt-{receipt.number}.pdf"'
        return response
