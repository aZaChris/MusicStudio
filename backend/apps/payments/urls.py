from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet
from .webhooks import StripeWebhookView

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    *router.urls,
]
