"""client_ip: trust only what our own proxies appended (ADR-021)."""

import pytest
from django.test import RequestFactory

from apps.common.net import client_ip


def _req(xff: str | None = None, remote: str = "10.0.0.2"):
    extra = {"HTTP_X_FORWARDED_FOR": xff} if xff is not None else {}
    return RequestFactory().get("/", REMOTE_ADDR=remote, **extra)


def test_no_trusted_proxy_uses_socket_address(settings):
    settings.TRUSTED_PROXY_COUNT = 0
    assert client_ip(_req("6.6.6.6")) == "10.0.0.2"


def test_one_proxy_takes_the_right_most_entry(settings):
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(_req("3.18.12.63")) == "3.18.12.63"


def test_forged_left_most_entry_is_ignored(settings):
    settings.TRUSTED_PROXY_COUNT = 1
    # The client sent "X-Forwarded-For: 3.18.12.63"; our proxy appended the real address.
    assert client_ip(_req("3.18.12.63, 6.6.6.6")) == "6.6.6.6"


@pytest.mark.parametrize("xff", [None, "", " , "])
def test_missing_header_falls_back_to_socket(settings, xff):
    settings.TRUSTED_PROXY_COUNT = 1
    assert client_ip(_req(xff)) == "10.0.0.2"


def test_two_proxies_skip_the_inner_one(settings):
    settings.TRUSTED_PROXY_COUNT = 2
    assert client_ip(_req("6.6.6.6, 1.2.3.4, 172.18.0.5")) == "1.2.3.4"
