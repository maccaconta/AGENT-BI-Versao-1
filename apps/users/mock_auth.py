"""
Mock Authentication for local rapid development without Cognito/JWT.
"""
from rest_framework.authentication import BaseAuthentication
from apps.users.models import User, Tenant, RoleChoices, TenantMember
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class LocalFastMockAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if not getattr(settings, "DEBUG", False):
            return None
        
        try:
            tenant_slug = request.headers.get("X-Tenant-Slug", "default")
            
            # Modo Local Fast: Em DEBUG, toda requisição local é tratada como admin mock.
            # Isso garante que o frontend consiga operar sem tokens Cognito reais.
            is_mock = True 
            
            if is_mock:
                # 1. Garante que o tenant exista
                tenant, _ = Tenant.objects.get_or_create(
                    slug=tenant_slug,
                    defaults={
                        "name": f"Tenant {tenant_slug.capitalize()}",
                        "s3_prefix": "agent-bi-local-dev",
                        "glue_database_prefix": "agent_bi_local",
                        "athena_workgroup": "primary"
                    }
                )
                
                # 2. Garante que o usuário admin exista (Busca por email primeiro para evitar conflitos de Unique)
                admin_email = "admin@agentbi.local"
                user = User.objects.filter(email=admin_email).first()
                
                if not user:
                    # Se não existe pelo email, verifica se existe pelo username 'admin'
                    user = User.objects.filter(username="admin").first()
                    
                    if not user:
                        # Se realmente não existe nenhum similar, cria um novo
                        user = User.objects.create(
                            email=admin_email,
                            username="admin",
                            full_name="Local Fast Admin",
                            is_super_admin=True,
                            primary_tenant=tenant
                        )
                
                # Garante que o admin mock tenha o tenant correto setado como primário
                if not user.primary_tenant:
                    user.primary_tenant = tenant
                    user.save()
                
                # 3. Garante vínculo e role de OWNER no tenant alvo
                member, _ = TenantMember.objects.get_or_create(
                    user=user,
                    tenant=tenant,
                    defaults={"role": RoleChoices.OWNER, "is_active": True}
                )
                
                if not member.is_active:
                    member.is_active = True
                    member.save()

                request.tenant = tenant
                return (user, None)
        except Exception as e:
            logger.error(f"[MOCK_AUTH] Erro ao resolver usuário/tenant mock: {str(e)}")
            return None
        
        return None
