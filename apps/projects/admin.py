from django.contrib import admin
from .models import Project, ProjectMember, DataDomain

@admin.register(DataDomain)
class DataDomainAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "owner", "created_at")
    list_filter = ("tenant", "owner")
    search_fields = ("name", "description")

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "domain", "status", "created_at")
    list_filter = ("status", "tenant", "domain")
    search_fields = ("name", "description")
    raw_id_fields = ("tenant", "domain", "default_dataset", "created_by", "updated_by")

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "project__name")
