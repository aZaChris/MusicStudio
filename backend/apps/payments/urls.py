"""Route dell'app payments, montate sotto /api/v1/ da config/urls.py."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .account_views import OnboardingView, PaymentAccountView, RefreshView, RestartView
from .instruction_views import OpenInstructionsView, PaymentInstructionsView
from .receipt_views import IssueReceiptView, ReceiptListView, ReceiptPdfView
from .register_views import RegisterCsvExportView, RegisterPdfExportView, RegisterSummaryView
from .views import PaymentViewSet
from .webhooks import StripeConnectWebhookView, StripeWebhookView

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # Conto di pagamento dello studio (fase 9): stato, onboarding, rilettura, ripartenza.
    path("payment-account/", PaymentAccountView.as_view(), name="payment-account"),
    path(
        "payment-account/onboarding/", OnboardingView.as_view(), name="payment-account-onboarding"
    ),
    path("payment-account/refresh/", RefreshView.as_view(), name="payment-account-refresh"),
    path("payment-account/restart/", RestartView.as_view(), name="payment-account-restart"),
    # Ricevute non fiscali (fase 8).
    path("payments/<int:pk>/receipt/", IssueReceiptView.as_view(), name="payment-receipt"),
    path("receipts/", ReceiptListView.as_view(), name="receipt-list"),
    path("receipts/<int:pk>/pdf/", ReceiptPdfView.as_view(), name="receipt-pdf"),
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
    # Eventi dei conti collegati degli studi (fase 9): stessa logica, segreto di firma diverso.
    path(
        "webhooks/stripe-connect/",
        StripeConnectWebhookView.as_view(),
        name="stripe-connect-webhook",
    ),
    *router.urls,
]
