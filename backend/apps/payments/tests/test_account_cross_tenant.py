"""Un conto di pagamento non attraversa mai gli studi (fase 9, FR-006, FR-031, SC-006).

Le rotte non hanno id nel URL: lo studio è sempre quello di chi chiama. Quindi "un altro studio"
non ha niente da indovinare: la prova è che ognuno vede e tocca solo il proprio.
"""

import pytest

from apps.common.factories import StudioPaymentAccountFactory, TeacherFactory
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import StudioPaymentAccount

pytestmark = pytest.mark.django_db
URL = "/api/v1/payment-account/"


def test_each_studio_reads_only_its_own_account(fake_stripe):
    a = make_studio_owner()
    b = make_studio_owner()
    StudioPaymentAccountFactory(studio=a.studio, state="active")
    StudioPaymentAccountFactory(studio=b.studio, state="restricted")
    b_teacher = TeacherFactory(studio=b.studio)

    assert client_for(a.user).get(URL).data["state"] == "active"
    assert client_for(b.user).get(URL).data["state"] == "restricted"
    assert client_for(b_teacher.user).get(URL).data["state"] == "restricted"
    nothing = make_studio_owner()
    assert client_for(nothing.user).get(URL).data["state"] == "not_started"


def test_a_refresh_never_reads_or_writes_another_studios_account(fake_stripe):
    a = make_studio_owner()
    b = make_studio_owner()
    account_b = StudioPaymentAccountFactory(studio=b.studio, state="information_needed")
    fake_stripe.set_account(account_b.stripe_account_id, card_payments="active")

    # A non ha un conto: il suo refresh è 404 e il conto di B non si muove.
    assert client_for(a.user).post(URL + "refresh/").status_code == 404

    account_b.refresh_from_db()
    assert account_b.state == "information_needed"
    assert fake_stripe.account_params == [] and fake_stripe.links == []


def test_starting_in_one_studio_never_touches_another_studios_account(fake_stripe):
    a = make_studio_owner()
    b = make_studio_owner()
    existing = StudioPaymentAccountFactory(studio=b.studio)

    assert client_for(a.user).post(URL + "onboarding/").status_code == 200

    assert StudioPaymentAccount.objects.count() == 2
    assert StudioPaymentAccount.objects.get(studio=b.studio).pk == existing.pk
    assert StudioPaymentAccount.objects.get(studio=a.studio).stripe_account_id != (
        existing.stripe_account_id
    )


def test_restart_only_removes_the_callers_own_dead_account(fake_stripe):
    a = make_studio_owner()
    b = make_studio_owner()
    StudioPaymentAccountFactory(studio=a.studio, state="disconnected")
    kept = StudioPaymentAccountFactory(studio=b.studio, state="disconnected")

    assert client_for(a.user).post(URL + "restart/").status_code == 204

    assert list(StudioPaymentAccount.objects.all()) == [kept]


def test_another_studios_teacher_cannot_read_or_change_this_studio(fake_stripe):
    a = make_studio_owner()
    StudioPaymentAccountFactory(studio=a.studio, state="active")
    stranger = TeacherFactory()  # un insegnante di un altro studio

    seen = client_for(stranger.user).get(URL).data

    assert seen["state"] == "not_started" and seen["needs_attention"] == []
    assert client_for(stranger.user).post(URL + "onboarding/").status_code == 403
