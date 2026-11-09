from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import (
    CanWriteTenantObject,
    IsStudioOwner,
    IsTeacherOrStudioOwner,
)
from apps.common.tenancy import get_tenant
from apps.lessons.selectors import lessons_of_student
from apps.lessons.serializers import LessonSerializer

from .models import Student
from .selectors import students_for
from .serializers import ReassignStudentSerializer, StudentSerializer
from .services import create_student, reassign_student


class StudentViewSet(viewsets.ModelViewSet[Student]):
    serializer_class = StudentSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_fields = ["is_active"]

    def get_queryset(self) -> QuerySet[Student]:
        return students_for(get_tenant(self.request))

    def perform_create(self, serializer: StudentSerializer) -> None:  # type: ignore[override]
        serializer.instance = create_student(get_tenant(self.request), **serializer.validated_data)

    # Without this the schema claimed a Student; typed clients (the mobile app) need the truth.
    @extend_schema(responses=LessonSerializer(many=True))
    @action(detail=True, methods=["get"], pagination_class=None, filter_backends=[])
    def lessons(self, request: Request, pk: str | None = None) -> Response:
        student = self.get_object()
        return Response(LessonSerializer(lessons_of_student(student), many=True).data)

    @extend_schema(request=ReassignStudentSerializer, responses=StudentSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsStudioOwner])
    def reassign(self, request: Request, pk: str | None = None) -> Response:
        """Studio owner only: give the student to another teacher of the same studio."""
        student = self.get_object()
        serializer = ReassignStudentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reassign_student(student, serializer.validated_data["teacher"])
        # Re-read through the selector so the response has the same shape as GET.
        refreshed = students_for(get_tenant(request)).get(pk=student.pk)
        return Response(StudentSerializer(refreshed).data)
