"""
apps.users.serializers
───────────────────────
Serializers para autenticação, usuários e tenants.
"""
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import Tenant, TenantInvitation, TenantMember, User


# ─── Tenant ───────────────────────────────────────────────────────────────────

class TenantSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "slug", "description", "status",
            "s3_prefix", "cognito_pool_id", "glue_database_prefix",
            "athena_workgroup", "max_projects", "max_datasets",
            "max_dashboards", "member_count", "created_at",
        ]
        read_only_fields = [
            "id", "s3_prefix", "cognito_pool_id",
            "glue_database_prefix", "athena_workgroup", "created_at",
        ]

    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()


class TenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["name", "slug", "description"]

    def validate_slug(self, value):
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Este slug já está em uso.")
        return value


# ─── User ─────────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    role_in_tenant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "full_name", "avatar_url",
            "is_active", "is_super_admin", "role_in_tenant",
            "last_active_at", "created_at",
        ]
        read_only_fields = ["id", "is_super_admin", "created_at"]

    def get_role_in_tenant(self, obj):
        request = self.context.get("request")
        if request and request.tenant:
            return obj.get_tenant_role(request.tenant)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "full_name", "password", "password_confirm"]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Senhas não conferem."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "avatar_url", "username"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Senhas não conferem."}
            )
        return data


# ─── TenantMember ─────────────────────────────────────────────────────────────

class TenantMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = TenantMember
        fields = [
            "id", "user", "role", "is_active",
            "invited_at", "accepted_at",
        ]
        read_only_fields = ["id", "user", "invited_at", "accepted_at"]


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=["ADMIN", "ANALYST", "APPROVER", "VIEWER"])


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


# ─── Auth JWT customizado ─────────────────────────────────────────────────────

class AgentBITokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT customizado com dados do usuário e tenant embutidos."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims customizados
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["is_super_admin"] = user.is_super_admin
        if user.primary_tenant:
            token["primary_tenant_slug"] = user.primary_tenant.slug
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Atualizar last_active_at
        self.user.last_active_at = timezone.now()
        self.user.save(update_fields=["last_active_at"])

        # Adicionar info do usuário na resposta
        data["user"] = UserSerializer(self.user, context=self.context).data
        return data


class MeSerializer(serializers.ModelSerializer):
    """Dados do usuário logado + todos os tenants."""
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "full_name", "avatar_url",
            "is_active", "is_super_admin", "memberships",
            "last_active_at", "created_at",
        ]

    def get_memberships(self, obj):
        memberships = obj.memberships.filter(
            is_active=True, is_deleted=False
        ).select_related("tenant")
        return [
            {
                "tenant_id": str(m.tenant.id),
                "tenant_name": m.tenant.name,
                "tenant_slug": m.tenant.slug,
                "role": m.role,
            }
            for m in memberships
        ]
