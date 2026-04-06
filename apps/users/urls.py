"""
apps.users.urls
───────────────
URL patterns para autenticação e usuários.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    AgentBITokenObtainPairView,
    MeView,
    RegisterView,
    TenantViewSet,
)

router = DefaultRouter()
router.register("tenants", TenantViewSet, basename="tenant")
router.register("register", RegisterView, basename="register")

urlpatterns = [
    # JWT
    path("token/", AgentBITokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Me / Profile
    path("me/", MeView.as_view({"get": "me"}), name="me"),
    path("me/update/", MeView.as_view({"patch": "update_me"}), name="me_update"),
    path(
        "me/change-password/",
        MeView.as_view({"post": "change_password"}),
        name="change_password",
    ),
    # Router
    path("", include(router.urls)),
]
