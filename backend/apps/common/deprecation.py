"""Deprecazione di un endpoint: segnali in ogni risposta, nel contratto e nel registro (ADR-040).

Un endpoint deprecato continua a funzionare uguale fino alla data di rimozione. Nel frattempo:
- ogni risposta porta `Deprecation` (RFC 9745), `Sunset` (RFC 8594) e `Link` (successore e policy);
- il contratto OpenAPI lo segna `deprecated: true`, con la data in testa alla descrizione;
- ogni chiamata lascia una riga di log `deprecated_call`, per sapere chi lo usa ancora;
- dalla data di rimozione risponde 410 con il codice `endpoint_gone`.
Il registro in memoria (`REGISTRY`) è la fonte di verità: un test lo confronta con
docs/operations/deprecations.md e il comando `deprecation_report` lo usa per il promemoria.
Spiegazione: docs/learning/concetti/versionamento-e-deprecazione-api.md.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, TypeVar

from django.conf import settings
from django.urls import get_resolver
from django.utils import timezone
from django.utils.http import http_date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import DomainError

POLICY_URL = (
    "https://github.com/aZaChris/MusicStudio/blob/main/docs/operations/api-versioning-policy.md"
)
logger = logging.getLogger("musicstudio.deprecation")
V = TypeVar("V", bound=type[APIView])


class EndpointGone(DomainError):
    """L'endpoint è stato rimosso alla data annunciata (HTTP 410)."""

    status_code = status.HTTP_410_GONE
    code = "endpoint_gone"


@dataclass(frozen=True)
class Deprecation:
    endpoint: str  # metodo e percorso, come nel registro: "GET /api/v1/lessons/"
    since: date
    sunset: date
    successor: str | None
    report: str  # percorso del rapporto di migrazione, dalla radice del repository

    @property
    def sunset_at(self) -> datetime:
        return datetime.combine(self.sunset, time.min, tzinfo=UTC)

    def headers(self) -> dict[str, str]:
        since_at = datetime.combine(self.since, time.min, tzinfo=UTC)
        links = [f'<{POLICY_URL}>; rel="deprecation"']
        if self.successor:
            links.insert(0, f'<{self.successor}>; rel="successor-version"')
        return {
            # RFC 9745: una data strutturata, "@" seguito dai secondi Unix.
            "Deprecation": f"@{int(since_at.timestamp())}",
            "Sunset": http_date(self.sunset_at.timestamp()),
            "Link": ", ".join(links),
        }


REGISTRY: list[Deprecation] = []


def _now() -> datetime:
    # Un punto solo da cui si legge l'ora: i test lo sostituiscono invece di fermare il tempo.
    return timezone.now()


def deprecated(
    *, endpoint: str, since: date, sunset: date, report: str, successor: str | None = None
) -> Callable[[V], V]:
    """Decoratore di classe per una APIView o un ViewSet deprecato."""
    minimum: int = settings.API_DEPRECATION_MIN_NOTICE_DAYS
    if (sunset - since).days < minimum:
        # Errore all'import, non in produzione: un preavviso troppo corto non arriva mai al deploy.
        raise ValueError(f"{endpoint}: notice must be at least {minimum} days before removal.")
    item = Deprecation(endpoint, since, sunset, successor, report)
    REGISTRY.append(item)

    def decorate(view_cls: V) -> V:
        class DeprecatedView(view_cls):  # type: ignore[valid-type,misc]
            def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
                if _now() >= item.sunset_at:
                    raise EndpointGone(
                        f"This endpoint was removed on {item.sunset.isoformat()}. See {POLICY_URL}."
                    )
                super().initial(request, *args, **kwargs)

            def finalize_response(
                self, request: Request, response: Response, *args: Any, **kwargs: Any
            ) -> Response:
                response = super().finalize_response(request, response, *args, **kwargs)
                for name, value in item.headers().items():
                    response[name] = value
                # Solo endpoint e client dichiarato: nessun dato della persona (constitution X).
                logger.info(
                    "deprecated_call",
                    extra={
                        "endpoint": item.endpoint,
                        "client": request.headers.get("X-Client", "")[:64],
                    },
                )
                return response

        # Stesso nome e modulo dell'originale: log, admin e schema non vedono la sottoclasse.
        for attr in ("__name__", "__qualname__", "__module__", "__doc__"):
            setattr(DeprecatedView, attr, getattr(view_cls, attr))
        description = f"Deprecated: removed on {sunset.isoformat()}. See {POLICY_URL}."
        original = inspect.getdoc(view_cls)
        if original:
            description = f"{description}\n\n{original}"
        schema = extend_schema(deprecated=True, description=description)
        return schema(DeprecatedView)  # type: ignore[return-value]

    return decorate


def load_registry() -> list[Deprecation]:
    """Il registro completo: importare gli URL importa le view, e i decoratori lo riempiono."""
    _ = get_resolver().url_patterns
    return REGISTRY


def register_problems(items: list[Deprecation], register_text: str, repo_root: Path) -> list[str]:
    """Ciò che manca nel registro Markdown o nei rapporti di migrazione (vuoto = tutto a posto)."""
    rows = [line for line in register_text.splitlines() if line.lstrip().startswith("|")]
    problems = []
    for item in items:
        if not any(item.endpoint in row and item.sunset.isoformat() in row for row in rows):
            problems.append(
                f"{item.endpoint}: no row with removal date {item.sunset} in the register."
            )
        if not (repo_root / item.report).is_file():
            problems.append(f"{item.endpoint}: migration report {item.report} does not exist.")
    return problems
