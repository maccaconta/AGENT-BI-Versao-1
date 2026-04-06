"""
Agent-BI — URL Configuration principal.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# ─── API v1 URL Patterns ──────────────────────────────────────────────────────
api_v1_patterns = [
    # Auth
    path("auth/", include("apps.users.urls")),
    # Core resources
    path("projects/", include("apps.projects.urls")),
    path("datasets/", include("apps.datasets.urls")),
    path("dashboards/", include("apps.dashboards.urls")),
    path("versions/", include("apps.versions.urls")),
    path("approvals/", include("apps.approvals.urls")),
    # Knowledge (Governança & Policies)
    path("governance/", include("apps.governance.urls")),
    path("templates/", include("apps.templates_lib.urls")),
    path("instructions/", include("apps.instructions.urls")),
    # AI & Infra
    path("copilot/", include("apps.ai_engine.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("infra/", include("apps.infra.urls")),
    # Audit & Compliance
    path("audit/", include("apps.audit.urls")),
]

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include(api_v1_patterns)),
    # API Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
