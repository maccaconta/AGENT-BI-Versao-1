"""
apps.users.middleware
──────────────────────
Injeção do tenant atual na request via header X-Tenant-Slug.
"""
import logging
from django.http import JsonResponse
from apps.users.models import Tenant, TenantMember

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    Resolve o tenant a partir do header X-Tenant-Slug ou
    do primary_tenant do usuário autenticado.

    Injeta request.tenant para uso nas views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None

        # Rotas públicas não precisam de tenant
        public_paths = [
            "/admin/",
            "/api/schema/",
            "/api/docs/",
            "/api/redoc/",
            "/api/v1/auth/token/",
            "/api/v1/auth/token/refresh/",
            "/api/v1/auth/register/",
        ]
        if any(request.path.startswith(p) for p in public_paths):
            return self.get_response(request)

        # Tenta resolver tenant
        tenant_slug = request.headers.get("X-Tenant-Slug")

        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug, is_deleted=False)

                # Verifica se usuário autenticado tem acesso
                if hasattr(request, "user") and request.user.is_authenticated:
                    if not request.user.is_super_admin:
                        is_member = TenantMember.objects.filter(
                            user=request.user,
                            tenant=tenant,
                            is_active=True,
                        ).exists()
                        if not is_member:
                            return JsonResponse(
                                {"detail": "Sem acesso a este tenant."},
                                status=403,
                            )

                request.tenant = tenant

            except Tenant.DoesNotExist:
                return JsonResponse(
                    {"detail": "Tenant não encontrado."},
                    status=404,
                )
        elif hasattr(request, "user") and request.user.is_authenticated:
            # Fallback: usa primary_tenant do usuário
            request.tenant = request.user.primary_tenant

        return self.get_response(request)
