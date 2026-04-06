"""
apps.users.permissions
───────────────────────
Classes de permissão RBAC multi-tenant.
"""
from rest_framework.permissions import BasePermission
from apps.users.models import RoleChoices


class IsAuthenticated(BasePermission):
    """Usuário autenticado com tenant resolvido."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
        )


class IsTenantMember(BasePermission):
    """Qualquer membro ativo do tenant."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        return request.user.get_tenant_role(request.tenant) is not None


class IsTenantOwner(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        return request.user.has_tenant_permission(request.tenant, RoleChoices.OWNER)


class IsTenantAdmin(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        return request.user.has_tenant_permission(request.tenant, RoleChoices.ADMIN)


class IsTenantAnalyst(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        return request.user.has_tenant_permission(request.tenant, RoleChoices.ANALYST)


class IsTenantApprover(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        role = request.user.get_tenant_role(request.tenant)
        return role in [RoleChoices.APPROVER, RoleChoices.ADMIN, RoleChoices.OWNER]


class IsTenantViewer(BasePermission):
    """Mínimo: visualizador."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_super_admin:
            return True
        if not request.tenant:
            return False
        return request.user.has_tenant_permission(request.tenant, RoleChoices.VIEWER)


class TenantObjectPermission(BasePermission):
    """
    Verifica se o objeto pertence ao tenant da request.
    Use em has_object_permission com objetos que têm campo `tenant`.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        tenant_field = getattr(obj, "tenant", None)
        if tenant_field is None:
            return True
        return tenant_field == request.tenant
