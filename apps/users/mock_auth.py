"""
Mock Authentication for local rapid development without Cognito/JWT.
"""
from rest_framework.authentication import BaseAuthentication
from apps.users.models import User, Tenant, RoleChoices, TenantMember
from django.conf import settings

class LocalFastMockAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if not getattr(settings, "DEBUG", False):
            return None
        
        auth_header = request.headers.get("Authorization", "")
        if "valid_mock_token" in auth_header:
            tenant, _ = Tenant.objects.get_or_create(
                slug="default",
                defaults={"name": "Default Tenant for Local Dev"}
            )
            
            user, created = User.objects.get_or_create(
                email="admin@agentbi.local",
                defaults={
                    "username": "admin",
                    "full_name": "Local Fast Admin",
                    "is_super_admin": True,
                    "primary_tenant": tenant
                }
            )
            
            if created:
                TenantMember.objects.get_or_create(
                    user=user,
                    tenant=tenant,
                    role=RoleChoices.OWNER
                )
                
            request.tenant = tenant
            return (user, None)
        
        return None
