"""Endpoint del conto di pagamento dello studio: titolare, insegnanti, altri (US1, fase 9)."""

import threading

import pytest
from django.db import connection

from apps.audit.models import AuditEntry
from apps.common.factories import (
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
    make_student_account,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import StudioPaymentAccount

pytestmark = pytest.mark.django_db
URL = "/api/v1/payment-account/"
ONBOARD = URL + "onboarding/"
REFRESH = URL + "refresh/"
RESTART = URL + "restart/"


def test_the_feature_switch_off_makes_every_route_not_found(settings):
    settings.ONLINE_PAYMENTS_ENABLED = False
    owner = make_studio_owner()
    client = client_for(owner.user)

    assert client.get(URL).status_code == 404
    for path in (ONBOARD, REFRESH, RESTART):
        assert client.post(path).status_code == 404
    assert not StudioPaymentAccount.objects.exists()


def test_a_studio_with_no_account_reads_not_started(fake_stripe):
    owner = make_studio_owner()

    res = client_for(owner.user).get(URL)

    assert res.status_code == 200
    assert res.data["state"] == "not_started" and res.data["can_accept_online"] is False
    assert res.data["dashboard_url"] is None and res.data["needs_attention"] == []
    assert res.data["test_mode"] is True


def test_the_owner_starts_onboarding_and_gets_the_stripe_page(fake_stripe):
    owner = make_studio_owner()

    res = client_for(owner.user).post(ONBOARD)

    assert res.status_code == 200
    assert res.data["url"].startswith("https://connect.stripe.com/setup/")
    account = StudioPaymentAccount.objects.get()
    assert account.studio_id == owner.studio_id and account.created_by_id == owner.user_id
    assert account.state == "information_needed"  # un conto nuovo aspetta i dati del titolare
    link = fake_stripe.links[0]
    assert link["account_id"] == account.stripe_account_id
    assert link["return_url"].endswith("/settings/payments?return=1")
    assert link["refresh_url"].endswith("/settings/payments?refresh=1")


def test_nothing_personal_is_sent_to_stripe_at_creation(fake_stripe):
    owner = make_studio_owner()

    client_for(owner.user).post(ONBOARD)

    assert fake_stripe.account_params == [
        {
            "studio_id": owner.studio_id,
            "idempotency_key": fake_stripe.account_params[0]["idempotency_key"],
        }
    ]


def test_starting_twice_reuses_the_account_and_resumes(fake_stripe):
    owner = make_studio_owner()
    client = client_for(owner.user)

    first = client.post(ONBOARD)
    second = client.post(ONBOARD)

    assert first.status_code == second.status_code == 200
    assert StudioPaymentAccount.objects.count() == 1
    assert len(fake_stripe.account_params) == 1  # Stripe è stata chiamata una volta sola
    assert first.data["url"] != second.data["url"]  # ma ogni volta un link nuovo


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_clicks_create_one_account(fake_stripe):
    owner = make_studio_owner()
    barrier = threading.Barrier(2)
    results: list[int] = []
    lock = threading.Lock()

    def click() -> None:
        try:
            client = client_for(owner.user)
            barrier.wait(timeout=5)
            code = client.post(ONBOARD).status_code
        except Exception:
            code = -1
        finally:
            connection.close()
        with lock:
            results.append(code)

    threads = [threading.Thread(target=click) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert results == [200, 200]
    assert StudioPaymentAccount.objects.count() == 1
    assert len(fake_stripe.account_params) == 1


def test_a_provider_error_leaves_nothing_stored(fake_stripe):
    owner = make_studio_owner()
    fake_stripe.fail_account = True

    res = client_for(owner.user).post(ONBOARD)

    assert res.status_code == 503 and res.data["code"] == "payments_unavailable"
    assert not StudioPaymentAccount.objects.exists()
    assert not AuditEntry.objects.filter(action="payment_account.start").exists()


def test_refresh_reads_stripe_and_updates_the_state_with_an_audit_entry(fake_stripe):
    owner = make_studio_owner()
    client = client_for(owner.user)
    client.post(ONBOARD)
    account = StudioPaymentAccount.objects.get()
    fake_stripe.set_account(account.stripe_account_id, card_payments="active")

    res = client.post(REFRESH)

    assert res.status_code == 200
    assert res.data["state"] == "active" and res.data["can_accept_online"] is True
    assert res.data["dashboard_url"].startswith("https://dashboard.stripe.com/test")
    entry = AuditEntry.objects.get(action="payment_account.state")
    assert entry.actor_id is None and entry.studio_id == owner.studio_id
    assert entry.metadata == {"from": "information_needed", "to": "active"}


def test_refreshing_an_unchanged_account_writes_no_new_audit_entry(fake_stripe):
    owner = make_studio_owner()
    client = client_for(owner.user)
    client.post(ONBOARD)

    client.post(REFRESH)
    client.post(REFRESH)

    assert not AuditEntry.objects.filter(action="payment_account.state").exists()


def test_refresh_without_an_account_is_not_found(fake_stripe):
    owner = make_studio_owner()

    res = client_for(owner.user).post(REFRESH)

    assert res.status_code == 404 and res.data["code"] == "no_payment_account"


def test_a_teacher_can_read_but_not_change(fake_stripe):
    owner = make_studio_owner()
    teacher = TeacherFactory(studio=owner.studio)
    client_for(owner.user).post(ONBOARD)
    client = client_for(teacher.user)

    assert client.get(URL).status_code == 200
    for path in (ONBOARD, REFRESH, RESTART):
        assert client.post(path).status_code == 403
    assert StudioPaymentAccount.objects.count() == 1


def test_parents_adult_students_and_anonymous_are_denied(fake_stripe):
    student = StudentFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)
    adult = make_student_account(StudentFactory())
    from rest_framework.test import APIClient

    for client in (client_for(parent.user), client_for(adult), APIClient()):
        assert client.get(URL).status_code in (401, 403)
        assert client.post(ONBOARD).status_code in (401, 403)


def test_restart_only_works_from_a_disconnected_account(fake_stripe):
    owner = make_studio_owner()
    client = client_for(owner.user)
    client.post(ONBOARD)
    account = StudioPaymentAccount.objects.get()

    assert client.post(RESTART).status_code == 409
    assert client.post(ONBOARD).status_code == 200

    account.state = "disconnected"
    account.save()
    assert client.post(ONBOARD).data["code"] == "account_disconnected"
    assert client.post(RESTART).status_code == 204
    assert not StudioPaymentAccount.objects.exists()
    assert client.post(ONBOARD).status_code == 200  # si può ricominciare: nuovo conto
    assert StudioPaymentAccount.objects.count() == 1


def test_audit_entries_hold_ids_and_state_names_only(fake_stripe):
    owner = make_studio_owner()
    client_for(owner.user).post(ONBOARD)

    entry = AuditEntry.objects.get(action="payment_account.start")

    assert entry.actor_id == owner.user_id and entry.studio_id == owner.studio_id
    assert entry.metadata == {"state": "information_needed"}


def test_the_account_endpoints_are_rate_limited(fake_stripe, settings):
    owner = make_studio_owner()
    client = client_for(owner.user)
    client.post(ONBOARD)

    codes = [client.post(REFRESH).status_code for _ in range(25)]

    assert 429 in codes  # il limite di prova è 20/min
