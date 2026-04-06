"""
apps.users.views
─────────────────
ViewSets para autenticação, usuários e tenants.
"""
import secrets
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.signals import audit_event
from apps.users.models import Tenant, TenantInvitation, TenantMember, User
from apps.users.permissions import IsTenantAdmin, IsTenantMember, IsTenantOwner
from apps.users.serializers import (
    AcceptInvitationSerializer,
    AgentBITokenObtainPairSerializer,
    ChangePasswordSerializer,
    InviteUserSerializer,
    MeSerializer,
    TenantCreateSerializer,
    TenantMemberSerializer,
    TenantSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.users.services.cognito_service import CognitoService


# ─── Auth Views ───────────────────────────────────────────────────────────────

class AgentBITokenObtainPairView(TokenObtainPairView):
    """Login com email/senha → JWT."""
    serializer_class = AgentBITokenObtainPairSerializer
    permission_classes = [AllowAny]


# ─── Register ─────────────────────────────────────────────────────────────────

class RegisterView(viewsets.GenericViewSet):
    """Registro de novo usuário."""
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    @action(detail=False, methods=["post"])
    def register(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        audit_event.send(
            sender=self.__class__,
            action="user.registered",
            user=user,
            resource_type="User",
            resource_id=user.id,
        )

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


# ─── Me / Profile ─────────────────────────────────────────────────────────────

class MeView(viewsets.GenericViewSet):
    """Perfil do usuário logado."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    @action(detail=False, methods=["patch"])
    def update_me(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeSerializer(request.user, context={"request": request}).data)

    @action(detail=False, methods=["post"])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"detail": "Senha atual incorreta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        audit_event.send(
            sender=self.__class__,
            action="user.password_changed",
            user=user,
            resource_type="User",
            resource_id=user.id,
        )

        return Response({"detail": "Senha alterada com sucesso."})


# ─── Tenant ViewSet ───────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(tags=["tenants"]),
    create=extend_schema(tags=["tenants"]),
    retrieve=extend_schema(tags=["tenants"]),
    update=extend_schema(tags=["tenants"]),
)
class TenantViewSet(viewsets.ModelViewSet):
    """CRUD de tenants."""
    queryset = Tenant.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        if self.action == "create":
            return TenantCreateSerializer
        return TenantSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        elif self.action in ["update", "partial_update", "destroy"]:
            return [IsTenantOwner()]
        return [IsTenantMember()]

    def perform_create(self, serializer):
        import uuid
        slug = serializer.validated_data["slug"]
        tenant = serializer.save(
            s3_prefix=f"tenant/{slug}",
            glue_database_prefix=f"agentbi_{slug}",
            athena_workgroup=f"agentbi-{slug}",
            created_by=self.request.user.id,
        )

        # Adicionar criador como OWNER
        TenantMember.objects.create(
            user=self.request.user,
            tenant=tenant,
            role="OWNER",
            accepted_at=timezone.now(),
        )

        # Definir como primary_tenant se não tiver
        if not self.request.user.primary_tenant:
            self.request.user.primary_tenant = tenant
            self.request.user.save(update_fields=["primary_tenant"])

        # Provisionar infraestrutura AWS
        from apps.infra.services.terraform_service import TerraformService
        TerraformService.provision_tenant_infra_async(tenant)

        audit_event.send(
            sender=self.__class__,
            action="tenant.created",
            user=self.request.user,
            resource_type="Tenant",
            resource_id=tenant.id,
        )

    # ── Members ──────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"], permission_classes=[IsTenantMember])
    def members(self, request, pk=None):
        tenant = self.get_object()
        members = TenantMember.objects.filter(
            tenant=tenant, is_active=True
        ).select_related("user")
        return Response(TenantMemberSerializer(members, many=True).data)

    @action(
        detail=True, methods=["post"],
        permission_classes=[IsTenantAdmin],
        url_path="members/invite",
    )
    def invite_member(self, request, pk=None):
        tenant = self.get_object()
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        # Criar convite
        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email=email,
            role=role,
            token=secrets.token_urlsafe(32),
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # TODO: enviar email via SES
        # ses_service.send_invitation_email(invitation)

        audit_event.send(
            sender=self.__class__,
            action="tenant.member_invited",
            user=request.user,
            resource_type="TenantInvitation",
            resource_id=invitation.id,
            extra={"email": email, "role": role},
        )

        return Response(
            {"detail": f"Convite enviado para {email}."},
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["patch"],
        permission_classes=[IsTenantAdmin],
        url_path=r"members/(?P<user_id>[^/.]+)/role",
    )
    def update_member_role(self, request, pk=None, user_id=None):
        tenant = self.get_object()
        new_role = request.data.get("role")

        if new_role not in ["ADMIN", "ANALYST", "APPROVER", "VIEWER"]:
            return Response(
                {"detail": "Role inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            membership = TenantMember.objects.get(
                tenant=tenant, user_id=user_id, is_active=True
            )
            old_role = membership.role
            membership.role = new_role
            membership.save()

            audit_event.send(
                sender=self.__class__,
                action="tenant.member_role_changed",
                user=request.user,
                resource_type="TenantMember",
                resource_id=membership.id,
                extra={"old_role": old_role, "new_role": new_role},
            )

            return Response(TenantMemberSerializer(membership).data)

        except TenantMember.DoesNotExist:
            return Response(
                {"detail": "Membro não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
