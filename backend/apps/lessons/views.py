"""Endpoint delle lezioni e della dashboard. Le view sono sottili: logica in services.py.

I docstring delle view finiscono in openapi.yaml: qui si usano commenti `#` (CLAUDE.md,
"Gotchas"). Permessi: docs/learning/concetti/permessi-drf.md e ADR-011.
"""

from typing import cast

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import CanWriteTenantObject, IsTeacherOrStudioOwner
from apps.common.tenancy import get_tenant

from . import selectors, services
from .cache import cached_dashboard
from .models import Lesson
from .serializers import (
    DashboardSerializer,
    LessonCancelSerializer,
    LessonCompleteSerializer,
    LessonSerializer,
)


@extend_schema(
    parameters=[
        OpenApiParameter(
            "week",
            OpenApiTypes.DATE,
            description="Any day of the week to list (list only; default: current week).",
        )
    ]
)
class LessonViewSet(viewsets.ModelViewSet[Lesson]):
    # CRUD delle lezioni più le azioni upcoming, complete e cancel. Solo insegnanti e titolari.
    serializer_class = LessonSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]

    def get_queryset(self) -> QuerySet[Lesson]:
        ctx = get_tenant(self.request)
        # L'elenco mostra una settimana alla volta (?week=...), per non caricare tutto lo storico.
        week_param = self.request.query_params.get("week")
        if self.action == "list" or week_param:
            return selectors.lessons_in_week(ctx, selectors.parse_week(week_param))
        return selectors.lessons_for(ctx)

    def perform_create(self, serializer: LessonSerializer) -> None:  # type: ignore[override]
        # Passa dal service: controlla il pacchetto e converte le sovrapposizioni in 409.
        serializer.instance = services.create_lesson(**serializer.validated_data)

    def perform_update(self, serializer: LessonSerializer) -> None:  # type: ignore[override]
        instance = cast(Lesson, serializer.instance)  # in aggiornamento è sempre valorizzato
        serializer.instance = services.update_lesson(instance, **serializer.validated_data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request: Request) -> Response:
        # Le prossime 3 lezioni in programma (per la home dell'app).
        lessons = selectors.upcoming_lessons_for(get_tenant(request))
        return Response(LessonSerializer(lessons, many=True).data)

    @extend_schema(request=LessonCompleteSerializer, responses=LessonSerializer)
    @action(detail=True, methods=["post"])
    def complete(self, request: Request, pk: str | None = None) -> Response:
        # Segna svolta e scala il pacchetto: vedi services.complete_lesson.
        serializer = LessonCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = services.complete_lesson(self.get_object(), note=serializer.validated_data["note"])
        return Response(LessonSerializer(lesson).data)

    @extend_schema(request=LessonCancelSerializer, responses=LessonSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        # Annulla o segna l'assenza: vedi services.cancel_lesson.
        serializer = LessonCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = services.cancel_lesson(
            self.get_object(), status=serializer.validated_data["status"]
        )
        return Response(LessonSerializer(lesson).data)


class DashboardView(APIView):
    # Dashboard dell'insegnante: lezioni della settimana, prossime, pagamenti in sospeso e
    # pacchetti in esaurimento. Il risultato è in cache (cache.py, ADR-017).
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]

    @extend_schema(responses=DashboardSerializer)
    def get(self, request: Request) -> Response:
        ctx = get_tenant(request)
        data = cached_dashboard(ctx, lambda: DashboardSerializer(selectors.dashboard_for(ctx)).data)
        return Response(data)
