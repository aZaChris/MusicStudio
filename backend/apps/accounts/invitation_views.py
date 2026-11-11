"""HTTP layer for invitations (contract: specs/007-security-privacy-accounts/contracts/api.md)."""

from typing import Any

from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.tenancy import get_tenant
from apps.common.throttling import ScopedRateThrottle

from . import invitations
from .models import Invitation, User


class IsTeacherOrOwnerRole(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        return getattr(request.user, "role", None) in (User.Role.TEACHER, User.Role.STUDIO_OWNER)


class InvitationSerializer(serializers.ModelSerializer[Invitation]):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )
    students: serializers.PrimaryKeyRelatedField[Any] = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ["id", "email", "role", "student_ids", "students", "status", "expires_at"]
        read_only_fields = ["expires_at"]

    def get_status(self, obj: Invitation) -> str:
        if obj.status == Invitation.Status.PENDING and obj.expires_at <= timezone.now():
            return "expired"
        return obj.status


class InvitationViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet[Invitation]
):
    serializer_class = InvitationSerializer
    permission_classes = [IsTeacherOrOwnerRole]

    def get_queryset(self) -> QuerySet[Invitation]:
        return invitations.invitations_visible_to(get_tenant(self.request))

    def perform_create(self, serializer: Any) -> None:
        data = serializer.validated_data
        serializer.instance = invitations.create_invitation(
            get_tenant(self.request),
            self.request.user,  # type: ignore[arg-type]
            email=data["email"],
            role=data["role"],
            student_ids=data["student_ids"],
        )

    @extend_schema(request=None, responses={200: InvitationSerializer})
    @action(detail=True, methods=["post"])
    def revoke(self, request: Request, pk: str | None = None) -> Response:
        invitation = self.get_object()
        invitations.revoke_invitation(request.user, invitation)  # type: ignore[arg-type]
        return Response(InvitationSerializer(invitation).data)


class InvitationLookupSerializer(serializers.Serializer[None]):
    role = serializers.CharField()
    studio_name = serializers.CharField()
    email = serializers.EmailField()
    student_first_names = serializers.ListField(child=serializers.CharField())
    existing_account = serializers.BooleanField()


class AcceptInvitationSerializer(serializers.Serializer[None]):
    token = serializers.CharField(max_length=128)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
        required=False,
        allow_blank=True,
        default="",
    )
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    accept_terms = serializers.BooleanField()
    consent = serializers.BooleanField(required=False, default=False)

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must accept the terms and privacy notice.")
        return value


class TokenPairSerializer(serializers.Serializer[None]):
    access = serializers.CharField()
    refresh = serializers.CharField()


class InvitationLookupView(APIView):
    """What the invitation is for, so the page can show it before asking for a password."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation_accept"

    @extend_schema(
        parameters=[OpenApiParameter("token", str, required=True)],
        responses={200: InvitationLookupSerializer},
    )
    def get(self, request: Request) -> Response:
        invitation = invitations.lookup(request.query_params.get("token", ""))
        if invitation is None:
            raise NotFound("This invitation is not valid any more.")
        return Response(
            {
                "role": invitation.role,
                "studio_name": invitation.studio.name,
                "email": invitation.email,
                "student_first_names": [s.first_name for s in invitation.students.all()],
                "existing_account": User.objects.filter(email__iexact=invitation.email).exists(),
            }
        )


class AcceptInvitationView(APIView):
    """Accept: a new account (with password) or, for a parent, the signed-in account."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation_accept"

    @extend_schema(request=AcceptInvitationSerializer, responses={201: TokenPairSerializer})
    def post(self, request: Request) -> Response:
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        signed_in = request.user if request.user.is_authenticated else None
        user = invitations.accept_invitation(
            data["token"],
            signed_in=signed_in,
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            consent=data["consent"],
        )
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )
