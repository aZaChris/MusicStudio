from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.common.permissions import IsStudioOwner

from .models import Teacher
from .serializers import StudioSerializer, TeacherSerializer


class MyStudioView(RetrieveAPIView):
    serializer_class = StudioSerializer
    permission_classes = [IsStudioOwner]

    def get_object(self):
        return self.request.user.teacher.studio


class StudioTeachersView(ListAPIView):
    serializer_class = TeacherSerializer
    permission_classes = [IsStudioOwner]

    def get_queryset(self):
        teacher = getattr(self.request.user, "teacher", None)
        if teacher is None:
            return Teacher.objects.none()
        return Teacher.objects.filter(studio=teacher.studio)
