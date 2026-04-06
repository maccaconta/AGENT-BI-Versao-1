from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataDomainViewSet, ProjectViewSet

router = DefaultRouter()
router.register(r'domains', DataDomainViewSet, basename='domains')
router.register(r'', ProjectViewSet, basename='projects')

urlpatterns = [
    path('', include(router.urls)),
]
