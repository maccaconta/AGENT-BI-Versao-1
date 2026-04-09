"""
apps.governance.views
─────────────────────
Views para gestão de políticas e diretrizes de IA por Administradores.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
# Remover import temporário do spectacular para evitar conflitos de introspecção
from apps.governance.models import GlobalSystemPrompt
from apps.shared_models import PromptTemplate
from apps.governance.serializers import GlobalSystemPromptSerializer, PromptTemplateSerializer

class PromptTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar a Biblioteca de Prompts Especialistas.
    Permite customizar as personas de Risco, Tesouraria, Compliance, etc.
    """
    serializer_class = PromptTemplateSerializer
    queryset = PromptTemplate.objects.all()
    pagination_class = None  # Desativa paginação para facilitar consumo no frontend corporativo
    permission_classes = [permissions.AllowAny] 
    authentication_classes = [] # Desativa autenticação para evitar erros de MockAuth em ambiente dev
    
    def get_queryset(self):
        # Retorna todos os templates públicos
        queryset = self.queryset.filter(is_public=True)
        category = self.request.query_params.get("category")
        
        # Log de debug para rastreamento (aparece no log do servidor Django)
        print(f"[DEBUG] PromptTemplate Query: category={category} | count={queryset.count()}")
        
        if category:
            # Filtro insensível a maiúsculas/minúsculas para maior resiliência
            queryset = queryset.filter(category__iexact=category)
            
        return queryset


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
