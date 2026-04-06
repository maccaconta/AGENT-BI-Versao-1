from django.db import IntegrityError
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response

from apps.audit.signals import audit_event
from apps.users.permissions import IsTenantAnalyst, IsTenantMember, TenantObjectPermission

from .models import DataDomain, Project
from .serializers import (
    DataDomainSerializer,
    ProjectIntakeCreateSerializer,
    ProjectSerializer,
)


def _is_platform_admin(user) -> bool:
    return bool(getattr(user, "is_super_admin", False) or getattr(user, "is_superuser", False))


@extend_schema(tags=["Governança & Data Mesh"])
class DataDomainViewSet(viewsets.ModelViewSet):
    """ViewSet para gestão de Domínios de Dados (Data Mesh)."""

    queryset = DataDomain.objects.all()
    serializer_class = DataDomainSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tenant"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        queryset = super().get_queryset().annotate(project_count=Count("projects"))
        if _is_platform_admin(self.request.user):
            return queryset
        if self.request.tenant:
            return queryset.filter(tenant=self.request.tenant)
        if self.request.user.is_authenticated and self.request.user.primary_tenant_id:
            return queryset.filter(tenant=self.request.user.primary_tenant)
        return queryset.none()

    def perform_create(self, serializer):
        if _is_platform_admin(self.request.user):
            serializer.save()
            return
        tenant = self.request.tenant or self.request.user.primary_tenant
        serializer.save(tenant=tenant, owner=self.request.user)


@extend_schema(tags=["Governança & Data Mesh"])
class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet de projetos com endpoint de intake para criação via frontend."""

    queryset = Project.objects.filter(is_deleted=False)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "domain"]
    search_fields = ["name", "description", "domain_data_owner"]
    ordering_fields = ["created_at", "name", "status"]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("tenant", "domain", "created_by", "updated_by")
        )
        if _is_platform_admin(self.request.user):
            return queryset
        if self.request.tenant:
            return queryset.filter(tenant=self.request.tenant)
        if self.request.user.is_authenticated and self.request.user.primary_tenant_id:
            return queryset.filter(tenant=self.request.user.primary_tenant)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectIntakeCreateSerializer
        return ProjectSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsTenantAnalyst(), TenantObjectPermission()]
        return [IsTenantMember(), TenantObjectPermission()]

    def create(self, request, *args, **kwargs):
        intake_serializer = self.get_serializer(data=request.data)
        intake_serializer.is_valid(raise_exception=True)
        payload = intake_serializer.validated_data

        tenant = request.tenant or request.user.primary_tenant
        if not tenant:
            return Response(
                {"detail": "Tenant não resolvido para criação do projeto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dashboard_name = payload["dashboard"]
        domain_name = payload["dataDomain"]
        domain_defaults = {
            "description": f"Domínio criado automaticamente para {dashboard_name}",
            "owner": request.user,
        }
        domain, _ = DataDomain.objects.get_or_create(
            tenant=tenant,
            name=domain_name,
            defaults=domain_defaults,
        )

        intake_metadata = {
            "dashboard": payload["dashboard"],
            "dataDomain": payload["dataDomain"],
            "domainDataOwner": payload.get("domainDataOwner", ""),
            "confidentiality": payload.get("confidentiality", ""),
            "crawlFrequency": payload.get("crawlFrequency", ""),
            "objective": payload.get("objective", ""),
            "source": "frontend.projects.new",
        }

        try:
            project = Project.objects.create(
                tenant=tenant,
                domain=domain,
                name=dashboard_name,
                description=payload.get("objective", ""),
                domain_data_owner=payload.get("domainDataOwner", ""),
                data_confidentiality=payload.get("confidentiality", ""),
                crawler_frequency=payload.get("crawlFrequency", ""),
                intake_metadata=intake_metadata,
                created_by=request.user,
            )
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "Já existe um projeto com esse dashboard neste tenant. "
                        "Use outro nome para continuar."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        audit_event.send(
            sender=self.__class__,
            action="project.created",
            user=request.user,
            tenant=tenant,
            resource_type="Project",
            resource_id=project.id,
            extra={
                "project_name": project.name,
                "domain": domain.name,
            },
        )

        response_serializer = ProjectSerializer(project, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
