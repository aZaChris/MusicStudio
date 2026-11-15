"""Route dell'app payments, montate sotto /api/v1/ da config/urls.py."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .instruction_views import OpenInstructionsView, PaymentInstructionsView
from .register_views import RegisterCsvExportView, RegisterPdfExportView, RegisterSummaryView
from .views import PaymentViewSet
from .webhooks import StripeWebhookView

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # Istruzioni di pagamento dello studio e, per le famiglie, quelle da mostrare (fase 8).
    path("payment-instructions/", PaymentInstructionsView.as_view(), name="payment-instructions"),
    path(
        "payment-instructions/open/",
        OpenInstructionsView.as_view(),
        name="payment-instructions-open",
    ),
    # Registro di cassa (fase 8). Prima del router: `payments/register/...` non deve essere
    # scambiato per un id di pagamento.
    path("payments/register/summary/", RegisterSummaryView.as_view(), name="register-summary"),
    path(
        "payments/register/export/csv/", RegisterCsvExportView.as_view(), name="register-export-csv"
    ),
    path(
        "payments/register/export/pdf/", RegisterPdfExportView.as_view(), name="register-export-pdf"
    ),
    # Chiamato da Stripe, non dal portale: ha un'autenticazione sua (la firma), vedi webhooks.py.
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    *router.urls,
]
