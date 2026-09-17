import datetime

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsTeacherOrStudioOwner, role_scoped_queryset
from apps.students.models import Student

from .models import Lesson
from .serializers import LessonCancelSerializer, LessonCompleteSerializer, LessonSerializer


def _week_bounds(anchor: datetime.date) -> tuple[datetime.date, datetime.date]:
    monday = anchor - datetime.timedelta(days=anchor.weekday())
    return monday, monday + datetime.timedelta(days=7)


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [IsTeacherOrStudioOwner]

    def get_queryset(self):
        qs = role_scoped_queryset(
            self.request.user,
            Lesson.objects.select_related("student", "teacher", "package"),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="student__parent_accounts",
        )
        week_param = self.request.query_params.get("week")
        if week_param or self.action == "list":
            anchor = (
                datetime.date.fromisoformat(week_param) if week_param else timezone.localdate()
            )
            start, end = _week_bounds(anchor)
            qs = qs.filter(start_time__date__gte=start, start_time__date__lt=end)
        return qs

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        qs = role_scoped_queryset(
            request.user,
            Lesson.objects.select_related("student").filter(
                status=Lesson.Status.SCHEDULED, start_time__gte=timezone.now()
            ),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="student__parent_accounts",
        ).order_by("start_time")[:3]
        return Response(LessonSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        lesson = self.get_object()
        serializer = LessonCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson.mark_completed(note=serializer.validated_data["note"])
        return Response(LessonSerializer(lesson).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        lesson = self.get_object()
        serializer = LessonCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lesson.cancel(serializer.validated_data["status"])
        return Response(LessonSerializer(lesson).data)


class DashboardView(APIView):
    permission_classes = [IsTeacherOrStudioOwner]

    def get(self, request):
        from apps.payments.models import Payment  # avoid import cycle at module load

        today = timezone.localdate()
        start, end = _week_bounds(today)

        lessons = role_scoped_queryset(
            request.user,
            Lesson.objects.select_related("student").filter(
                start_time__date__gte=start, start_time__date__lt=end
            ),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="student__parent_accounts",
        ).order_by("start_time")

        upcoming = role_scoped_queryset(
            request.user,
            Lesson.objects.select_related("student").filter(
                status=Lesson.Status.SCHEDULED, start_time__gte=timezone.now()
            ),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="student__parent_accounts",
        ).order_by("start_time")[:3]

        students = role_scoped_queryset(
            request.user,
            Student.objects.filter(is_active=True),
            teacher_field="teacher",
            studio_field="teacher__studio",
            parent_field="parent_accounts",
        )

        pending_payments = role_scoped_queryset(
            request.user,
            Payment.objects.filter(status=Payment.Status.PENDING),
            teacher_field="student__teacher",
            studio_field="student__teacher__studio",
            parent_field="student__parent_accounts",
        )

        low_package_students = [s for s in students if (p := s.active_package) and p.is_low]

        return Response(
            {
                "week": LessonSerializer(lessons, many=True).data,
                "upcoming": LessonSerializer(upcoming, many=True).data,
                "pending_payments_count": pending_payments.count(),
                "active_students_count": students.count(),
                "low_package_students": [
                    {"id": s.id, "full_name": s.full_name} for s in low_package_students
                ],
            }
        )
