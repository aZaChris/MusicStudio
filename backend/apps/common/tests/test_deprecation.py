"""Il decoratore @deprecated: segnali in ogni risposta e nel contratto, poi 410 (ADR-040)."""

import logging
from datetime import UTC, date, datetime

import pytest
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.common import deprecation

SINCE = date(2026, 12, 1)
SUNSET = date(2027, 3, 31)


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    # Le view di prova non devono finire nel registro vero, che il test del registro confronta
    # con docs/operations/deprecations.md.
    monkeypatch.setattr(deprecation, "REGISTRY", [])


@pytest.fixture
def freezer(monkeypatch):
    # Niente librerie per fermare il tempo: il modulo legge l'ora da `_now`, che qui si sostituisce.
    class Clock:
        def move_to(self, value: str) -> None:
            moment = datetime.fromisoformat(value).replace(tzinfo=UTC)
            monkeypatch.setattr(deprecation, "_now", lambda: moment)

    return Clock()


def make_view(successor: str | None = "/api/v2/things/") -> type[APIView]:
    @deprecation.deprecated(
        endpoint="GET /api/v1/things/",
        since=SINCE,
        sunset=SUNSET,
        successor=successor,
        report="docs/operations/migrations/things.md",
    )
    class ThingsView(APIView):
        authentication_classes: list[type] = []
        permission_classes = [AllowAny]

        def get(self, request):
            return Response({"things": [1, 2]})

    return ThingsView


def call(view: type[APIView], **headers: str):
    request = APIRequestFactory().get("/api/v1/things/", **headers)
    return view.as_view()(request)


def test_response_is_unchanged_and_carries_the_signals(freezer):
    freezer.move_to("2027-01-10")
    res = call(make_view())
    assert res.status_code == 200
    assert res.data == {"things": [1, 2]}
    # RFC 9745: data strutturata, secondi Unix della data di deprecazione (mezzanotte UTC).
    assert res["Deprecation"] == "@1796083200"
    assert res["Sunset"] == "Wed, 31 Mar 2027 00:00:00 GMT"
    assert '</api/v2/things/>; rel="successor-version"' in res["Link"]
    assert 'rel="deprecation"' in res["Link"]


def test_link_has_no_successor_when_none_is_given(freezer):
    freezer.move_to("2027-01-10")
    res = call(make_view(successor=None))
    assert "successor-version" not in res["Link"]
    assert 'rel="deprecation"' in res["Link"]


def test_after_the_sunset_date_the_endpoint_is_gone(freezer):
    freezer.move_to("2027-03-31 00:00:01")
    res = call(make_view())
    assert res.status_code == 410
    assert res.data["code"] == "endpoint_gone"
    assert "2027-03-31" in res.data["detail"]


def test_a_notice_shorter_than_the_policy_is_refused():
    with pytest.raises(ValueError, match="90"):
        deprecation.deprecated(
            endpoint="GET /api/v1/x/",
            since=date(2027, 1, 1),
            sunset=date(2027, 2, 1),
            report="docs/operations/migrations/x.md",
        )


def test_every_call_leaves_one_log_line_without_personal_data(freezer, caplog):
    freezer.move_to("2027-01-10")
    view = make_view()
    with caplog.at_level(logging.INFO, logger="musicstudio.deprecation"):
        call(view, HTTP_X_CLIENT="mobile/1.4.2")
    [line] = [r for r in caplog.records if r.name == "musicstudio.deprecation"]
    assert line.getMessage() == "deprecated_call"
    assert line.endpoint == "GET /api/v1/things/"
    assert line.client == "mobile/1.4.2"
    assert not hasattr(line, "user_id")


@pytest.mark.django_db
def test_signals_cost_no_query(freezer, django_assert_num_queries):
    freezer.move_to("2027-01-10")
    view = make_view()
    with django_assert_num_queries(0):
        call(view)


def test_contract_marks_the_operation_deprecated_with_the_removal_date():
    view = make_view()
    schema = SchemaGenerator(patterns=[path("api/v1/things/", view.as_view())]).get_schema(
        request=None, public=True
    )
    operation = schema["paths"]["/api/v1/things/"]["get"]
    assert operation["deprecated"] is True
    assert operation["description"].startswith("Deprecated: removed on 2027-03-31.")


def test_the_registry_records_each_deprecation():
    make_view()
    [item] = deprecation.REGISTRY
    assert (item.endpoint, item.sunset, item.successor) == (
        "GET /api/v1/things/",
        SUNSET,
        "/api/v2/things/",
    )
