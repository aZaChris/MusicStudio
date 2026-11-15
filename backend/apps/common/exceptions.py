"""Eccezioni di dominio e gestore delle eccezioni di DRF.

I service sollevano `django.core.exceptions.ValidationError`, così restano indipendenti dal
livello HTTP (li chiamano anche i task Celery, l'admin e i comandi di gestione). Questo gestore
trasforma quegli errori nella stessa risposta 400 che DRF usa per gli errori dei serializer, e
`DomainConflict` (un conflitto di stato, ad esempio un orario occupato) in un 409.
Spiegazione: docs/learning/concetti/service-layer-e-modular-monolith.md.
"""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Un rifiuto di dominio, con uno stato HTTP e un codice leggibile da una macchina."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code = "error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DomainConflict(DomainError):
    """La richiesta è valida ma in conflitto con lo stato attuale dei dati (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class PeriodTooLong(DomainError):
    """Un periodo di esportazione oltre il massimo consentito (HTTP 400, fase 8)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "period_too_long"


class ServiceUnavailable(DomainError):
    """Una dipendenza (es. il gateway di pagamento) non è configurata o non risponde (503)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "unavailable"


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # Impostato in REST_FRAMEWORK['EXCEPTION_HANDLER']: tutte le view passano da qui.
    if isinstance(exc, DomainError):
        return Response({"detail": exc.detail, "code": exc.code}, status=exc.status_code)
    # Un ValidationError di Django dei service diventa il 400 che DRF darebbe per un serializer.
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        exc = DRFValidationError(detail=detail)
    return drf_exception_handler(exc, context)
