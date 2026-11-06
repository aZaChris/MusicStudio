from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import IsTeacherOrStudioOwner
from apps.common.tenancy import get_tenant
from apps.lessons.selectors import lessons_of_student
from apps.lessons.serializers import LessonSerializer

from .models import Student
from .selectors import students_for
from .serializers import StudentSerializer
from .services import create_student


class StudentViewSet(viewsets.ModelViewSet[Student]):
    serializer_class = StudentSerializer
    permission_classes = [IsTeacherOrStudioOwner]
    filterset_fields = ["is_active"]

    def get_queryset(self) -> QuerySet[Student]:
        return students_for(get_tenant(self.request))

    def perform_create(self, serializer: StudentSerializer) -> None:  # type: ignore[override]
        serializer.instance = create_student(get_tenant(self.request), **serializer.validated_data)

    @action(detail=True, methods=["get"])
    def lessons(self, request: Request, pk: str | None = None) -> Response:
        student = self.get_object()
        return Response(LessonSerializer(lessons_of_student(student), many=True).data)
