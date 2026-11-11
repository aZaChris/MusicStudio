from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ConfirmEmailView,
    LogoutView,
    MeView,
    MfaConfirmView,
    MfaDisableView,
    MfaRecoveryCodesView,
    MfaSetupView,
    MfaStatusView,
    MfaVerifyView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendConfirmationView,
    ThrottledTokenObtainPairView,
)

urlpatterns = [
    path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("register/", RegisterView.as_view(), name="register"),
    path("confirm-email/", ConfirmEmailView.as_view(), name="confirm-email"),
    path("confirm-email/resend/", ResendConfirmationView.as_view(), name="confirm-email-resend"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("mfa/", MfaStatusView.as_view(), name="mfa-status"),
    path("mfa/setup/", MfaSetupView.as_view(), name="mfa-setup"),
    path("mfa/confirm/", MfaConfirmView.as_view(), name="mfa-confirm"),
    path("mfa/disable/", MfaDisableView.as_view(), name="mfa-disable"),
    path("mfa/recovery-codes/", MfaRecoveryCodesView.as_view(), name="mfa-recovery-codes"),
    path("mfa/verify/", MfaVerifyView.as_view(), name="mfa-verify"),
]
