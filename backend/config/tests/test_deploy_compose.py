"""Guards on the production Compose file (ADR-003, ADR-025): reviewed once, kept true by CI."""

from pathlib import Path

import pytest
import yaml
from django.conf import settings

ROOT = Path(settings.BASE_DIR).parent
SERVICES = yaml.safe_load((ROOT / "docker-compose.coolify.yml").read_text())["services"]
# The optional backup overlay (ADR-026) follows the same rules when someone does use it.
BACKUP_OVERLAY = yaml.safe_load((ROOT / "docker-compose.backup.yml").read_text())["services"]
ALL = {**SERVICES, **BACKUP_OVERLAY}


@pytest.mark.parametrize("name", sorted(ALL))
def test_no_service_publishes_a_host_port(name):
    # Coolify's proxy routes by domain; a published port would bypass it (and its HTTPS).
    assert "ports" not in ALL[name]


@pytest.mark.parametrize("name", sorted(ALL))
def test_every_service_has_a_healthcheck(name):
    assert "healthcheck" in ALL[name]


def test_backups_are_not_part_of_the_coolify_deploy():
    # The server's operator backs up the database (ADR-026); the overlay is opt-in only.
    assert {"backup", "offsite"}.isdisjoint(SERVICES)


def test_the_web_portal_is_built_for_production_and_only_exposed():
    web = SERVICES["web"]
    assert web["build"]["target"] == "prod"
    assert web["expose"] == ["8080"]
    assert web["environment"]["API_ORIGIN"] == "${API_PUBLIC_URL:?}"


def test_browser_calls_to_the_api_default_to_the_portal_origin_only():
    cors = SERVICES["backend"]["environment"]["CORS_ALLOWED_ORIGINS"]
    assert cors == "${CORS_ALLOWED_ORIGINS:-${SERVICE_URL_WEB_8080}}"


@pytest.mark.parametrize("dockerfile", ["backend/Dockerfile", "frontend/Dockerfile"])
def test_the_shipped_image_stage_has_no_run_step(dockerfile):
    # Coolify injects every variable, secrets included, as a build ARG; a RUN in the final
    # stage would write them into the image history (docker history).
    text = (ROOT / dockerfile).read_text()
    final_stage = text[text.rindex("\nFROM ") :]
    assert not any(line.lstrip().startswith("RUN ") for line in final_stage.splitlines())


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_every_service_has_a_memory_limit(name):
    # The server is shared with other apps: a runaway container must not starve them.
    assert "mem_limit" in SERVICES[name]
