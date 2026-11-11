"""Request id, access log and JSON formatter (US3, ADR-019)."""

import json
import logging
import sys
from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from apps.common import logging as rlog
from apps.common.factories import TeacherFactory
from apps.common.tests.helpers import client_for

pytestmark = pytest.mark.django_db


def test_valid_incoming_request_id_is_echoed():
    res = APIClient().get("/health/live/", HTTP_X_REQUEST_ID="demo-123")
    assert res["X-Request-ID"] == "demo-123"


@pytest.mark.parametrize("bad", ["", "has space", "x" * 65, "line\nbreak", "semi;colon"])
def test_unsafe_or_missing_id_is_replaced(bad):
    res = APIClient().get("/health/live/", HTTP_X_REQUEST_ID=bad)
    assert res["X-Request-ID"] != bad
    assert len(res["X-Request-ID"]) == 32


def test_access_line_has_route_status_duration_and_tenant(caplog):
    teacher = TeacherFactory()
    with caplog.at_level(logging.INFO, logger="musicstudio.access"):
        client_for(teacher.user).get("/api/v1/lessons/", HTTP_X_REQUEST_ID="req-1")

    record = next(r for r in caplog.records if r.name == "musicstudio.access")
    assert (record.method, record.status, record.route) == ("GET", 200, "api/v1/lessons/")
    assert record.user_id == teacher.user.pk
    assert record.studio_id == teacher.studio_id
    assert record.duration_ms >= 0
    assert rlog.request_id_var.get() == "-"  # reset after the request


def test_django_error_log_line_keeps_the_request_id(caplog):
    # django.request logs 4xx/5xx after the middleware chain: the id must still be set.
    caplog.handler.addFilter(rlog.RequestIdFilter())  # like the console handler: at emit time
    with caplog.at_level(logging.WARNING, logger="django.request"):
        APIClient().get("/api/v1/lessons/", HTTP_X_REQUEST_ID="req-401")

    record = next(r for r in caplog.records if r.name == "django.request")
    assert record.request_id == "req-401"
    assert rlog.request_id_var.get() == "-"  # cleared once the response is closed


def _format(record: logging.LogRecord) -> dict:
    rlog.RequestIdFilter().filter(record)
    return json.loads(rlog.JsonFormatter().format(record))


def test_json_formatter_outputs_one_object_with_extras():
    token = rlog.request_id_var.set("abc")
    try:
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "hi %s", ("you",), None)
        record.status = 201
        data = _format(record)
    finally:
        rlog.request_id_var.reset(token)

    assert data["msg"] == "hi you"
    assert (data["level"], data["logger"], data["request_id"]) == ("INFO", "x", "abc")
    assert data["status"] == 201
    assert data["ts"].endswith("+00:00")


def test_json_formatter_includes_the_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())

    data = _format(record)

    assert "ValueError: boom" in data["exc"]
    assert "\n" not in rlog.JsonFormatter().format(record)  # still a single line


def test_request_id_travels_to_celery_tasks():
    headers: dict = {}
    token = rlog.request_id_var.set("req-42")
    try:
        rlog.stamp_task_headers(headers=headers)
    finally:
        rlog.request_id_var.reset(token)
    assert headers == {"request_id": "req-42"}

    task = SimpleNamespace(request=SimpleNamespace(request_id="req-42"))
    rlog.bind_task_request_id(task=task)
    assert rlog.request_id_var.get() == "req-42"
    rlog.unbind_task_request_id(task=task)
    assert rlog.request_id_var.get() == "-"


def test_no_header_outside_a_request_and_unsafe_task_ids_ignored():
    headers: dict = {}
    rlog.stamp_task_headers(headers=headers)
    assert headers == {}

    task = SimpleNamespace(request=SimpleNamespace(request_id="bad id\n"))
    rlog.bind_task_request_id(task=task)
    rlog.unbind_task_request_id(task=task)
    assert rlog.request_id_var.get() == "-"


def test_task_args_filter_strips_arguments_but_keeps_the_rest():
    from apps.common.logging import TaskArgsFilter

    record = logging.LogRecord("celery.app.trace", 20, "p", 1, "Task succeeded", (), None)
    record.data = {"id": "abc", "runtime": 0.1, "args": "[1, 'secret-token']", "kwargs": "{}"}

    assert TaskArgsFilter().filter(record) is True
    assert record.data == {"id": "abc", "runtime": 0.1}
