"""Guards on the production Compose file (ADR-003, ADR-025): reviewed once, kept true by CI."""

from pathlib import Path

import pytest
import yaml
from django.conf import settings

COMPOSE = Path(settings.BASE_DIR).parent / "docker-compose.coolify.yml"
SERVICES = yaml.safe_load(COMPOSE.read_text())["services"]


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_no_service_publishes_a_host_port(name):
    # Coolify's proxy routes by domain; a published port would bypass it (and its HTTPS).
    assert "ports" not in SERVICES[name]


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_every_service_has_a_healthcheck(name):
    assert "healthcheck" in SERVICES[name]


def test_the_web_portal_is_built_for_production_and_only_exposed():
    web = SERVICES["web"]
    assert web["build"]["target"] == "prod"
    assert web["expose"] == ["8080"]
    assert web["environment"]["API_ORIGIN"] == "${API_PUBLIC_URL:?}"


def test_browser_calls_to_the_api_default_to_the_portal_origin_only():
    cors = SERVICES["backend"]["environment"]["CORS_ALLOWED_ORIGINS"]
    assert cors == "${CORS_ALLOWED_ORIGINS:-${SERVICE_URL_WEB_8080}}"
