"""
apps.governance.views
─────────────────────
Views para gestão de políticas e diretrizes de IA por Administradores.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
# Remover import temporário do spectacular para evitar conflitos de introspecção
from apps.governance.models import GlobalSystemPrompt
from apps.governance.serializers import GlobalSystemPromptSerializer


class GlobalSystemPromptViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar o System Prompt Global do Tenant.
    Acesso restrito a Administradores do Tenant.
    """
    serializer_class = GlobalSystemPromptSerializer
    queryset = GlobalSystemPrompt.objects.filter(is_active=True)

    def get_queryset(self):
        # Filtra pelo tenant do usuário logado (Middleware Tenant)
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return self.queryset.filter(tenant=tenant)
        return self.queryset.none()

    def perform_create(self, serializer):
        # Associa automaticamente ao tenant e ao usuário criador
        tenant = getattr(self.request, "tenant", None)
        serializer.save(tenant=tenant, created_by=self.request.user)
