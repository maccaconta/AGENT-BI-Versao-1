from django.contrib import admin
from apps.shared_models import PromptTemplate
from .models import GlobalSystemPrompt

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
