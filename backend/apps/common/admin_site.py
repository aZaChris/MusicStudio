"""L'admin di Django riservato agli operatori (ADR-041, specs/010 US2).

L'admin è l'unico posto che salta l'isolamento per studio, quindi lo chiudiamo in un punto solo:
- entra solo un operatore (`User.is_operator`): un ruolo di studio riceve 404 anche con is_staff;
- in produzione serve il codice TOTP (`ADMIN_REQUIRE_TOTP`), con il servizio MFA dell'API;
- password o codice sbagliati contano per lo stesso blocco dell'accesso all'API;
- con `ADMIN_ALLOWED_IPS` impostato, gli altri indirizzi ricevono 404 anche sulla pagina di login;
- ogni accesso, riuscito o no, finisce nel registro come `admin.login`.
Spiegazione: docs/learning/concetti/admin-blindato.md.
"""

from __future__ import annotations

from typing import Any, NoReturn

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
from django.http import Http404, HttpRequest, HttpResponse

from apps.accounts import mfa, services
from apps.accounts.models import User
from apps.audit import services as audit

from .net import client_ip


def ip_allowed(request: HttpRequest) -> bool:
    allowed: list[str] = settings.ADMIN_ALLOWED_IPS
    return not allowed or client_ip(request) in allowed


class OperatorLoginForm(AdminAuthenticationForm):
    otp = forms.CharField(
        label="One-time code", required=False, max_length=20, strip=True
    )  # testo dell'interfaccia in inglese, come il resto dell'admin

    def clean(self) -> dict[str, Any]:
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not email or not password:
            return self.cleaned_data  # errori dei singoli campi, già mostrati dal form
        email = services.normalize_email(email)
        known = User.objects.filter(email=email).first()
        # Bloccato: stesso messaggio di una password sbagliata, come nell'API (ADR-028).
        if known is not None and services.is_locked(known):
            self._deny(known)
        user = authenticate(self.request, username=email, password=password)
        if user is None:
            if known is not None:
                services.register_login_failure(known)
            self._deny(known)
        if not isinstance(user, User) or not user.is_operator:
            # Password giusta ma non è un operatore: rifiuto generico, senza contare un errore.
            self._deny(user)
        if settings.ADMIN_REQUIRE_TOTP:
            code = self.cleaned_data.get("otp") or ""
            if not (mfa.is_enabled(user) and mfa.check_second_factor(user, code)):
                services.register_login_failure(user)
                self._deny(user)
        services.register_login_success(user)
        audit.record(audit.Action.ADMIN_LOGIN, actor=user)
        self.user_cache = user
        return self.cleaned_data

    def _deny(self, user: User | None) -> NoReturn:
        audit.record(audit.Action.ADMIN_LOGIN, actor=user, outcome=audit.Outcome.FAILURE)
        raise self.get_invalid_login_error()


class OperatorAdminSite(admin.AdminSite):
    login_form = OperatorLoginForm
    login_template = "admin/operator_login.html"
    site_header = "MusicStudio operator admin"

    def has_permission(self, request: HttpRequest) -> bool:
        user = request.user
        return isinstance(user, User) and user.is_operator

    def admin_view(self, view: Any, cacheable: bool = False) -> Any:
        protected = super().admin_view(view, cacheable)

        def gate(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            # 404 e non 403: a chi non deve entrare l'admin non conferma nemmeno di esistere.
            if not ip_allowed(request):
                raise Http404
            if request.user.is_authenticated and not self.has_permission(request):
                raise Http404
            response: HttpResponse = protected(request, *args, **kwargs)
            return response

        return gate

    def login(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        if not ip_allowed(request):
            raise Http404
        return super().login(request, extra_context)
