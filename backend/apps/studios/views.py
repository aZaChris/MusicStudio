from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.common.permissions import IsStudioOwner

from .models import Studio, Teacher
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
        return Teacher.objects.filter(studio=self.request.user.teacher.studio)
