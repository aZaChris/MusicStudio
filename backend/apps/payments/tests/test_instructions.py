"""Payment instructions: the owner saves them, teachers read, parents see them beside open
packages (US3, FR-018..FR-024)."""

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEntry
from apps.common.factories import (
    PackageFactory,
    ParentAccountFactory,
    PaymentFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
    make_reversal,
    make_student_account,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import PaymentInstructions

pytestmark = pytest.mark.django_db

URL = "/api/v1/payment-instructions/"
OPEN = "/api/v1/payment-instructions/open/"
IBAN = "IT60X0542811101000000123456"
GOOD = {
    "account_holder": "Studio Armonia SRL",
    "iban": "IT60 X054 2811 1010 0000 0123 456",
    "bank_name": "Banca Esempio",
    "note": "Write the student's name in the reason",
    "links": [{"label": "PayPal", "url": "https://paypal.me/armonia"}],
}


def _save(owner, **overrides):
    return client_for(owner.user).put(URL, {**GOOD, **overrides}, format="json")


def test_an_owner_saves_and_reads_back_normalised_instructions():
    owner = make_studio_owner()

    saved = _save(owner)
    read = client_for(owner.user).get(URL)

    assert saved.status_code == 200 and read.status_code == 200
    assert read.data["iban"] == IBAN  # spaces removed, upper case
    assert read.data["account_holder"] == "Studio Armonia SRL"
    assert read.data["links"] == [{"label": "PayPal", "url": "https://paypal.me/armonia"}]
    assert read.data["updated_at"] is not None


def test_without_saved_instructions_the_fields_are_empty():
    owner = make_studio_owner()
    data = client_for(owner.user).get(URL).data

    assert data["iban"] == "" and data["links"] == [] and data["updated_at"] is None


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"iban": "IT60X0542811101000000123457"}, "iban"),  # bad checksum
        ({"iban": "not an iban"}, "iban"),
        ({"account_holder": ""}, "account_holder"),  # an IBAN needs its holder
        ({"links": [{"label": "Pay", "url": "http://paypal.me/x"}]}, "links"),  # not https
        ({"links": [{"label": "Pay", "url": "javascript:alert(1)"}]}, "links"),
        ({"links": [{"label": "Pay", "url": "https://"}]}, "links"),
        ({"links": [{"label": "Pay", "url": "https://a b.example"}]}, "links"),
        ({"links": [{"label": "", "url": "https://a.example"}]}, "links"),
        ({"links": [{"label": "x" * 41, "url": "https://a.example"}]}, "links"),
        ({"links": [{"label": "Pay", "url": "https://a.example/" + "x" * 500}]}, "links"),
        ({"links": [{"label": f"L{i}", "url": "https://a.example"} for i in range(6)]}, "links"),
    ],
)
def test_invalid_input_is_refused_with_a_clear_field_error(overrides, field):
    owner = make_studio_owner()

    res = _save(owner, **overrides)

    assert res.status_code == 400 and field in res.data
    assert not PaymentInstructions.objects.exists()


def test_five_links_are_allowed_and_a_note_alone_is_valid():
    owner = make_studio_owner()
    links = [{"label": f"L{i}", "url": f"https://a{i}.example"} for i in range(5)]

    assert _save(owner, links=links).status_code == 200
    only_note = client_for(owner.user).put(
        URL, {"note": "Pay in cash at the studio"}, format="json"
    )
    assert only_note.status_code == 200 and only_note.data["iban"] == ""


def test_teachers_read_but_cannot_change_and_families_cannot_call_the_studio_endpoint():
    owner = make_studio_owner()
    _save(owner)
    teacher = TeacherFactory(studio=owner.studio)
    parent = ParentAccountFactory()

    assert client_for(teacher.user).get(URL).data["iban"] == IBAN
    assert client_for(teacher.user).put(URL, GOOD, format="json").status_code == 403
    assert client_for(parent.user).get(URL).status_code == 403
    assert client_for(parent.user).put(URL, GOOD, format="json").status_code == 403
    assert APIClient().get(URL).status_code == 401
    assert APIClient().put(URL, GOOD, format="json").status_code == 401


def test_an_empty_body_removes_the_instructions():
    owner = make_studio_owner()
    _save(owner)

    res = client_for(owner.user).put(URL, {}, format="json")

    assert res.status_code == 200 and res.data["iban"] == ""
    assert not PaymentInstructions.objects.exists()
    assert AuditEntry.objects.filter(action="instructions.change").count() == 2


def test_every_change_is_audited_with_field_names_and_never_values():
    owner = make_studio_owner()

    _save(owner)
    _save(owner)  # identical second save: nothing changed, nothing recorded
    _save(owner, note="New note")

    entries = list(AuditEntry.objects.filter(action="instructions.change").order_by("id"))
    assert len(entries) == 2
    assert entries[0].metadata == {
        "fields": "account_holder,iban,bank_name,note,links",
        "cleared": False,
    }
    assert entries[1].metadata == {"fields": "note", "cleared": False}
    assert (entries[0].actor_id, entries[0].studio_id) == (owner.user.pk, owner.studio.pk)
    everything = " ".join(str(e.metadata) for e in AuditEntry.objects.all())
    assert IBAN not in everything and "Armonia" not in everything and "paypal" not in everything


def _family(owner):
    student = StudentFactory(teacher=owner)
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)
    return student, parent


def test_a_parent_sees_the_instructions_beside_an_open_package_only():
    owner = make_studio_owner()
    _save(owner)
    student, parent = _family(owner)
    package = PackageFactory(student=student)
    client = client_for(parent.user)

    rows = client.get(OPEN).data

    assert len(rows) == 1
    row = rows[0]
    assert row["studio_id"] == owner.studio.pk and row["studio_name"] == owner.studio.name
    assert row["student_ids"] == [student.pk]
    assert row["iban"] == IBAN and row["links"][0]["label"] == "PayPal"
    assert "not verified" in row["notice"]

    payment = PaymentFactory(student=student, package=package)  # paid: nothing left to pay
    assert client.get(OPEN).data == []
    make_reversal(payment)  # reversed: payable again
    assert len(client.get(OPEN).data) == 1


def test_nothing_without_an_open_package_or_without_saved_instructions():
    owner = make_studio_owner()
    student, parent = _family(owner)
    client = client_for(parent.user)

    assert client.get(OPEN).data == []  # instructions saved, but no package at all
    _save(owner)
    assert client.get(OPEN).data == []  # still no open package
    PackageFactory(student=student)
    assert len(client.get(OPEN).data) == 1

    client_for(owner.user).put(URL, {}, format="json")  # removed
    assert client.get(OPEN).data == []  # disappears at once


def test_a_parent_with_children_in_two_studios_gets_each_studios_instructions():
    first, second = make_studio_owner(), make_studio_owner()
    _save(first, account_holder="First Studio")
    _save(second, account_holder="Second Studio", iban="DE89 3704 0044 0532 0130 00")
    parent = ParentAccountFactory()
    for owner in (first, second):
        child = StudentFactory(teacher=owner)
        link_parent_to_student(parent, child)
        PackageFactory(student=child)

    rows = client_for(parent.user).get(OPEN).data

    assert {(r["studio_name"], r["account_holder"]) for r in rows} == {
        (first.studio.name, "First Studio"),
        (second.studio.name, "Second Studio"),
    }


def test_an_adult_student_sees_the_instructions_of_their_own_open_package():
    owner = make_studio_owner()
    _save(owner)
    student = StudentFactory(teacher=owner)
    PackageFactory(student=student)
    user = make_student_account(student)

    assert len(client_for(user).get(OPEN).data) == 1


def test_staff_cannot_use_the_family_endpoint():
    owner = make_studio_owner()
    _save(owner)

    assert client_for(owner.user).get(OPEN).status_code == 403
    assert APIClient().get(OPEN).status_code == 401


def test_the_list_says_which_children_have_an_open_package_so_siblings_do_not_mix():
    owner = make_studio_owner()
    _save(owner)
    parent = ParentAccountFactory()
    owing, settled = StudentFactory(teacher=owner), StudentFactory(teacher=owner)
    for child in (owing, settled):
        link_parent_to_student(parent, child)
    PackageFactory(student=owing)  # still to pay
    PaymentFactory(student=settled, package=PackageFactory(student=settled))  # already paid

    rows = client_for(parent.user).get(OPEN).data

    assert len(rows) == 1 and rows[0]["student_ids"] == [owing.pk]
