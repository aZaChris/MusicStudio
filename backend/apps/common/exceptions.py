"""Domain exceptions and the DRF exception handler.

Services raise `django.core.exceptions.ValidationError` so they stay independent of the
HTTP layer (they are also called from Celery tasks, the admin and management commands).
This handler turns those errors into the same 400 response DRF uses for serializer errors,
and `DomainConflict` (a state conflict, e.g. an occupied time slot) into a 409.
"""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """A domain-level refusal with an HTTP status and a machine-readable code."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code = "error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DomainConflict(DomainError):
    """The request is valid but conflicts with the current state of the data (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ServiceUnavailable(DomainError):
    """A dependency (e.g. the payment provider) is not configured or not reachable (503)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "unavailable"


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response({"detail": exc.detail, "code": exc.code}, status=exc.status_code)
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        exc = DRFValidationError(detail=detail)
    return drf_exception_handler(exc, context)
