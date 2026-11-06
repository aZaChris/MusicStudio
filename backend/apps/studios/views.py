from django.db.models import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.common.permissions import IsStudioOwner

from .models import Studio, Teacher
from .selectors import studio_for_owner, teachers_for_owner
from .serializers import StudioSerializer, TeacherSerializer


class MyStudioView(RetrieveAPIView[Studio]):
    serializer_class = StudioSerializer
    permission_classes = [IsStudioOwner]

    def get_object(self) -> Studio:
        studio = studio_for_owner(self.request.user)
        if studio is None:
            raise NotFound("No studio is linked to this account.")
        return studio


class StudioTeachersView(ListAPIView[Teacher]):
    serializer_class = TeacherSerializer
    permission_classes = [IsStudioOwner]

    def get_queryset(self) -> QuerySet[Teacher]:
        return teachers_for_owner(self.request.user)
