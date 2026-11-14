"""Route dell'app payments, montate sotto /api/v1/ da config/urls.py."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet
from .webhooks import StripeWebhookView

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # Chiamato da Stripe, non dal portale: ha un'autenticazione sua (la firma), vedi webhooks.py.
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    *router.urls,
]
