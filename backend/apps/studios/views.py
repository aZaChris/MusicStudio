"""Endpoint dello studio: solo il titolare vede il proprio studio e i suoi insegnanti.

Le view sono sottili. I docstring finiscono in openapi.yaml: qui si usano commenti `#`.
Permessi: docs/learning/concetti/permessi-drf.md e ADR-011.
"""

from django.db.models import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.common.permissions import IsStudioOwner
from apps.common.tenancy import get_tenant

from .models import Studio, Teacher
from .selectors import studio_for_owner, teachers_for_owner
from .serializers import StudioSerializer, TeacherSerializer


class MyStudioView(RetrieveAPIView[Studio]):
    # GET /studio/: lo studio del titolare che chiama, con il numero di insegnanti.
    serializer_class = StudioSerializer
    permission_classes = [IsStudioOwner]

    def get_object(self) -> Studio:
        # Lo studio non arriva da un id nell'URL ma dal tenant dell'utente: non c'è modo di
        # chiedere lo studio di un altro (docs/learning/concetti/isolamento-tenant-e-bola.md).
        studio = studio_for_owner(get_tenant(self.request))
        if studio is None:
            raise NotFound("No studio is linked to this account.")
        return studio


class StudioTeachersView(ListAPIView[Teacher]):
    # GET /studio/teachers/: gli insegnanti dello studio del titolare.
    serializer_class = TeacherSerializer
    permission_classes = [IsStudioOwner]

    def get_queryset(self) -> QuerySet[Teacher]:
        return teachers_for_owner(get_tenant(self.request))
