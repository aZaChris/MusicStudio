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
    serializer_class = LessonSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]

    def get_queryset(self) -> QuerySet[Lesson]:
        ctx = get_tenant(self.request)
        week_param = self.request.query_params.get("week")
        if self.action == "list" or week_param:
            return selectors.lessons_in_week(ctx, selectors.parse_week(week_param))
        return selectors.lessons_for(ctx)

    def perform_create(self, serializer: LessonSerializer) -> None:  # type: ignore[override]
        serializer.instance = services.create_lesson(**serializer.validated_data)

    def perform_update(self, serializer: LessonSerializer) -> None:  # type: ignore[override]
        instance = cast(Lesson, serializer.instance)  # always set on update
        serializer.instance = services.update_lesson(instance, **serializer.validated_data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request: Request) -> Response:
        lessons = selectors.upcoming_lessons_for(get_tenant(request))
        return Response(LessonSerializer(lessons, many=True).data)

    @extend_schema(request=LessonCompleteSerializer, responses=LessonSerializer)
    @action(detail=True, methods=["post"])
    def complete(self, request: Request, pk: str | None = None) -> Response:
        serializer = LessonCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = services.complete_lesson(self.get_object(), note=serializer.validated_data["note"])
        return Response(LessonSerializer(lesson).data)

    @extend_schema(request=LessonCancelSerializer, responses=LessonSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        serializer = LessonCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson = services.cancel_lesson(
            self.get_object(), status=serializer.validated_data["status"]
        )
        return Response(LessonSerializer(lesson).data)


class DashboardView(APIView):
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]

    @extend_schema(responses=DashboardSerializer)
    def get(self, request: Request) -> Response:
        ctx = get_tenant(request)
        data = cached_dashboard(ctx, lambda: DashboardSerializer(selectors.dashboard_for(ctx)).data)
        return Response(data)
