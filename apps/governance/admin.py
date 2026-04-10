from django.contrib import admin
from apps.shared_models import PromptTemplate
from .models import GlobalSystemPrompt, AgentSystemPrompt

@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "version", "is_public", "created_at")
    list_filter = ("category", "is_public")
    search_fields = ("name", "description", "content")
    ordering = ("-created_at",)
    
@admin.register(GlobalSystemPrompt)
class GlobalSystemPromptAdmin(admin.ModelAdmin):
    list_display = ("persona_title", "is_active", "tenant", "created_at")
    list_filter = ("is_active", "tenant")
    search_fields = ("persona_title", "persona_description")

@admin.register(AgentSystemPrompt)
class AgentSystemPromptAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_key", "version", "is_active", "created_at")
    list_filter = ("is_active", "agent_key")
    search_fields = ("name", "agent_key", "content", "description")
    ordering = ("agent_key",)
