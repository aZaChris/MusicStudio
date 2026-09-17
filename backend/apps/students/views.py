from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import IsTeacherOrStudioOwner, role_scoped_queryset
from apps.lessons.serializers import LessonSerializer

from .models import Student
from .serializers import StudentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsTeacherOrStudioOwner]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        return role_scoped_queryset(
            self.request.user,
            Student.objects.select_related("teacher"),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="parent_accounts",
        )

    @action(detail=True, methods=["get"])
    def lessons(self, request, pk=None):
        student = self.get_object()
        lessons = student.lessons.select_related("teacher").order_by("-start_time")
        return Response(LessonSerializer(lessons, many=True).data)
