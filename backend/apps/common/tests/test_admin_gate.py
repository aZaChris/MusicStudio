"""Chi entra nell'admin: solo operatori attivi, con TOTP in produzione e i blocchi dell'API.

ADR-041, specs/010 US2 (FR-005, FR-006, FR-009).
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.test import Client
from django.utils import timezone

from apps.accounts import mfa, totp
from apps.accounts.models import User
from apps.audit.models import AuditEntry

pytestmark = pytest.mark.django_db
PW = "Pianoforte-Verde-31"
ADMIN = "/" + settings.ADMIN_URL
LOGIN = ADMIN + "login/"


def make_operator(**extra) -> User:
    return User.objects.create_user(
        username="op",
        email="op@example.com",
        password=PW,
        is_staff=True,
        is_superuser=True,
        **extra,
    )


def sign_in(code: str = "", client: Client | None = None):
    client = client or Client()
    return client.post(LOGIN, {"username": "op@example.com", "password": PW, "otp": code})


def logged_in(response) -> bool:
    # L'admin di Django risponde 302 dopo un accesso riuscito e 200 (il form con l'errore) se no.
    return response.status_code == 302


@pytest.mark.parametrize("role", [r.value for r in User.Role])
def test_studio_roles_never_reach_the_admin_even_with_staff_flags(role):
    user = User.objects.create_user(
        username=role,
        email=f"{role}@example.com",
        password=PW,
        role=role,
        is_staff=True,
        is_superuser=True,
    )
    client = Client()
    client.force_login(user)
    assert client.get(ADMIN).status_code == 404
    login = Client().post(LOGIN, {"username": user.email, "password": PW})
    assert not logged_in(login)


def test_an_operator_reaches_the_admin():
    client = Client()
    client.force_login(make_operator())
    assert client.get(ADMIN).status_code == 200


def test_anonymous_visitors_get_the_login_page():
    assert Client().get(ADMIN).status_code == 302
    assert Client().get(LOGIN).status_code == 200


def test_without_totp_requirement_the_password_is_enough_and_audited(settings):
    settings.ADMIN_REQUIRE_TOTP = False
    operator = make_operator()
    assert logged_in(sign_in())
    entry = AuditEntry.objects.get(action="admin.login", outcome="success")
    assert entry.actor_id == operator.pk


def test_an_inactive_operator_cannot_sign_in(settings):
    settings.ADMIN_REQUIRE_TOTP = False
    make_operator(is_active=False)
    assert not logged_in(sign_in())


def test_operators_can_enrol_totp():
    assert mfa.is_eligible(make_operator())


def test_totp_is_required_when_switched_on(settings):
    settings.ADMIN_REQUIRE_TOTP = True
    operator = make_operator()
    # Senza secondo fattore attivo non si entra, nemmeno con la password giusta.
    assert not logged_in(sign_in())
    secret, _ = mfa.begin_setup(operator)
    recovery = mfa.confirm_setup(operator, totp.code_at(secret, totp.current_step()))
    assert not logged_in(sign_in("000000"))
    operator.refresh_from_db()
    assert operator.failed_logins == 2  # anche il codice sbagliato conta per il blocco
    assert logged_in(sign_in(recovery[0]))
    assert AuditEntry.objects.filter(action="admin.login", outcome="failure").count() == 2


def test_a_locked_operator_gets_the_same_message_as_a_wrong_password(settings):
    settings.ADMIN_REQUIRE_TOTP = False
    operator = make_operator()
    wrong = Client().post(LOGIN, {"username": operator.email, "password": "wrong-password"})
    User.objects.filter(pk=operator.pk).update(locked_until=timezone.now() + timedelta(hours=1))
    locked = sign_in()
    assert not logged_in(locked)
    assert locked.context["form"].non_field_errors() == wrong.context["form"].non_field_errors()


def test_five_wrong_passwords_lock_the_operator_like_the_api(settings):
    settings.ADMIN_REQUIRE_TOTP = False
    operator = make_operator()
    for _ in range(5):
        Client().post(LOGIN, {"username": operator.email, "password": "wrong-password"})
    operator.refresh_from_db()
    assert operator.locked_until is not None
    assert not logged_in(sign_in())


def test_clients_outside_the_allowlist_see_nothing(settings):
    settings.ADMIN_ALLOWED_IPS = ["10.0.0.1"]
    operator = make_operator()
    outside = Client(REMOTE_ADDR="10.0.0.2")
    assert outside.get(LOGIN).status_code == 404
    outside.force_login(operator)
    assert outside.get(ADMIN).status_code == 404
    inside = Client(REMOTE_ADDR="10.0.0.1")
    inside.force_login(operator)
    assert inside.get(ADMIN).status_code == 200
