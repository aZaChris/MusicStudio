from django.urls import path
from rest_framework.routers import SimpleRouter

from .invitation_views import AcceptInvitationView, InvitationLookupView, InvitationViewSet

router = SimpleRouter()
router.register("invitations", InvitationViewSet, basename="invitation")

urlpatterns = [
    path("invitations/lookup/", InvitationLookupView.as_view(), name="invitation-lookup"),
    path("invitations/accept/", AcceptInvitationView.as_view(), name="invitation-accept"),
    *router.urls,
]
