from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.audit.views import ExecutionTraceViewSet

router = DefaultRouter()
router.register(r"traces", ExecutionTraceViewSet, basename="execution-trace")

urlpatterns = [
    path("", include(router.urls)),
]
