"""
apps.users.models
─────────────────
Tenant, User, Role e controle de acesso multi-tenant.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampedModel(models.Model):
    """Mixin de timestamps e soft-delete."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class TenantStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    SUSPENDED = "SUSPENDED", "Suspenso"
    TRIAL = "TRIAL", "Trial"


class Tenant(TimeStampedModel):
    """
    Unidade de isolamento multi-tenant.
    Cada organização cliente é um Tenant.
    """
    name = models.CharField(max_length=255, verbose_name="Nome")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Descrição")
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.ACTIVE,
    )
    # AWS isolation
    s3_prefix = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Prefixo S3",
        help_text="Prefixo único no Data Lake S3",
    )
    cognito_pool_id = models.CharField(
        max_length=100, blank=True, verbose_name="Cognito Pool ID"
    )
    glue_database_prefix = models.CharField(
        max_length=100, blank=True, verbose_name="Prefixo Glue Database"
    )
    athena_workgroup = models.CharField(
        max_length=100, blank=True, verbose_name="Athena Workgroup"
    )
    # Settings
    max_projects = models.PositiveIntegerField(default=10)
    max_datasets = models.PositiveIntegerField(default=50)
    max_dashboards = models.PositiveIntegerField(default=100)
    # Audit
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "tenants"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @property
    def is_active(self):
        return self.status == TenantStatus.ACTIVE


class RoleChoices(models.TextChoices):
    OWNER = "OWNER", "Proprietário"
    ADMIN = "ADMIN", "Administrador"
    ANALYST = "ANALYST", "Analista"
    APPROVER = "APPROVER", "Aprovador"
    VIEWER = "VIEWER", "Visualizador"


class User(AbstractUser, TimeStampedModel):
    """
    Usuário customizado com suporte multi-tenant.
    Herda de AbstractUser para compatibilidade com Django admin.
    """
    # Override AbstractUser fields para usar UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True, verbose_name="E-mail")
    full_name = models.CharField(max_length=255, blank=True, verbose_name="Nome Completo")
    avatar_url = models.URLField(blank=True, verbose_name="Avatar URL")

    # Cognito integration
    cognito_sub = models.CharField(
        max_length=255, blank=True, unique=True, null=True,
        verbose_name="Cognito Sub",
        help_text="Subject do JWT do Cognito",
    )

    # Primary tenant (usuário pode ser membro de vários)
    primary_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_users",
        verbose_name="Tenant Principal",
    )

    # Flags
    is_super_admin = models.BooleanField(
        default=False,
        verbose_name="Super Admin",
        help_text="Acesso irrestrito ao sistema (apenas para admins da plataforma)",
    )
    last_active_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.full_name or self.email}"

    def get_tenant_role(self, tenant: Tenant) -> str | None:
        """Retorna o role do usuário em um tenant específico."""
        try:
            membership = self.memberships.get(tenant=tenant, is_active=True)
            return membership.role
        except TenantMember.DoesNotExist:
            return None

    def has_tenant_permission(self, tenant: Tenant, required_role: str) -> bool:
        """Verifica se o usuário tem pelo menos o role requerido no tenant."""
        if self.is_super_admin:
            return True
        role = self.get_tenant_role(tenant)
        if not role:
            return False
        role_hierarchy = [
            RoleChoices.VIEWER,
            RoleChoices.APPROVER,
            RoleChoices.ANALYST,
            RoleChoices.ADMIN,
            RoleChoices.OWNER,
        ]
        try:
            user_level = role_hierarchy.index(role)
            required_level = role_hierarchy.index(required_role)
            return user_level >= required_level
        except ValueError:
            return False


class TenantMember(TimeStampedModel):
    """
    Associação usuário-tenant com role.
    Um usuário pode ser membro de vários tenants com roles diferentes.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Usuário",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Tenant",
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.VIEWER,
        verbose_name="Role",
    )
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_sent",
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tenant_members"
        verbose_name = "Membro do Tenant"
        verbose_name_plural = "Membros do Tenant"
        unique_together = [("user", "tenant")]
        ordering = ["tenant", "role"]

    def __str__(self):
        return f"{self.user.email} @ {self.tenant.slug} ({self.role})"


class TenantInvitation(TimeStampedModel):
    """Convite para novo membro de um tenant."""
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField(verbose_name="E-mail Convidado")
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    token = models.CharField(max_length=255, unique=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations"
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        db_table = "tenant_invitations"

    def __str__(self):
        return f"Convite: {self.email} → {self.tenant.slug}"
