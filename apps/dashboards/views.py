"""
apps.dashboards.views
ViewSets para geracao, publicacao e consulta de dashboards.
"""
import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.signals import audit_event
from apps.dashboards.models import Dashboard, GenerationJob
from apps.dashboards.serializers import (
    DashboardCreateSerializer,
    DashboardSerializer,
    GenerateDashboardSerializer,
    GenerationJobSerializer,
)
from apps.users.permissions import IsTenantAnalyst, IsTenantMember, TenantObjectPermission

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(tags=["dashboards"]),
    create=extend_schema(tags=["dashboards"]),
    retrieve=extend_schema(tags=["dashboards"]),
    update=extend_schema(tags=["dashboards"]),
    destroy=extend_schema(tags=["dashboards"]),
)
class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de dashboards."""

    def get_queryset(self):
        qs = Dashboard.objects.filter(is_deleted=False)
        if self.request.tenant:
            qs = qs.filter(project__tenant=self.request.tenant)
        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.select_related("project", "current_version", "instruction", "created_by")

    def get_serializer_class(self):
        if self.action == "create":
            return DashboardCreateSerializer
        if self.action == "generate":
            return GenerateDashboardSerializer
        return DashboardSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "generate"]:
            return [IsTenantAnalyst(), TenantObjectPermission()]
        return [IsTenantMember(), TenantObjectPermission()]

    def perform_create(self, serializer):
        dashboard = serializer.save(created_by=self.request.user)
        audit_event.send(
            sender=self.__class__,
            action="dashboard.created",
            user=self.request.user,
            tenant=self.request.tenant,
            resource_type="Dashboard",
            resource_id=dashboard.id,
        )

    @extend_schema(
        tags=["dashboards"],
        summary="Gerar dashboard com IA",
        description="Inicia o pipeline incremental de geracao de dashboard.",
    )
    @action(detail=True, methods=["post"], url_path="generate")
    def generate(self, request, pk=None):
        """
        Inicia geracao de dashboard com IA.
        Retorna Job ID para acompanhamento de progresso.
        """
        dashboard = self.get_object()
        serializer = GenerateDashboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instruction_text = serializer.validated_data.get("instruction", "")
        dataset_id = serializer.validated_data.get("dataset_id")
        template_id = serializer.validated_data.get("template_id")

        from apps.datasets.models import Dataset, DatasetStatus

        try:
            dataset = Dataset.objects.get(
                id=dataset_id,
                project=dashboard.project,
                is_deleted=False,
            )
        except Dataset.DoesNotExist:
            return Response(
                {"detail": "Dataset nao encontrado neste projeto."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if dataset.status != DatasetStatus.READY:
            return Response(
                {"detail": f"Dataset nao esta pronto. Status atual: {dataset.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = GenerationJob.objects.create(
            dashboard=dashboard,
            status=GenerationJob.Status.PENDING,
            input_payload={
                "instruction": instruction_text,
                "dataset_id": str(dataset_id),
                "template_id": str(template_id) if template_id else None,
            },
            requested_by=request.user,
        )

        from apps.dashboards.tasks import generate_dashboard_task

        generate_dashboard_task.delay(str(job.id))

        audit_event.send(
            sender=self.__class__,
            action="dashboard.generation_started",
            user=request.user,
            tenant=request.tenant,
            resource_type="Dashboard",
            resource_id=dashboard.id,
            extra={"job_id": str(job.id), "dataset_id": str(dataset_id)},
        )

        return Response(
            {
                "job_id": str(job.id),
                "status": "PENDING",
                "message": "Geracao iniciada. Acompanhe via /jobs/{id}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], url_path=r"jobs/(?P<job_id>[^/.]+)")
    def job_status(self, request, job_id=None):
        """Consulta status de um job de geracao."""
        try:
            job = GenerationJob.objects.get(id=job_id)
        except GenerationJob.DoesNotExist:
            return Response(
                {"detail": "Job nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(GenerationJobSerializer(job).data)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        """Publica a versao aprovada do dashboard via CloudFront."""
        dashboard = self.get_object()

        if not dashboard.current_version:
            return Response(
                {"detail": "Dashboard nao possui versao aprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.versions.models import VersionState

        if dashboard.current_version.state != VersionState.APPROVED:
            return Response(
                {"detail": "Versao atual nao esta aprovada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.dashboards.services.publish_service import PublishService

        try:
            publish_service = PublishService()
            url = publish_service.publish_dashboard(dashboard, request.user)

            audit_event.send(
                sender=self.__class__,
                action="dashboard.published",
                user=request.user,
                tenant=request.tenant,
                resource_type="Dashboard",
                resource_id=dashboard.id,
                extra={"url": url},
            )

            return Response({
                "cloudfront_url": url,
                "published_at": dashboard.published_at,
            })
        except Exception as exc:
            logger.error("Erro ao publicar dashboard: %s", exc)
            return Response(
                {"detail": "Erro ao publicar dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="copilot")
    def copilot(self, request, pk=None):
        """
        Refina o dashboard atual via chat com o Agente BI.
        Dispara uma nova iteracao do pipeline incremental.
        """
        dashboard = self.get_object()
        message = (request.data.get("message") or "").strip()

        if not message:
            return Response(
                {"detail": "Mensagem vazia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_instruction = ""
        if dashboard.current_version and dashboard.current_version.instruction_snapshot:
            base_instruction = dashboard.current_version.instruction_snapshot.get("content", "")

        combined_instruction = (
            f"{base_instruction}\n\nRefinamento solicitado pelo usuario:\n{message}"
            if base_instruction
            else message
        )

        dataset = dashboard.project.datasets.filter(is_deleted=False, status="READY").first()
        if not dataset:
            return Response(
                {"detail": "Nenhum dataset pronto disponivel neste projeto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = GenerationJob.objects.create(
            dashboard=dashboard,
            status=GenerationJob.Status.PENDING,
            input_payload={
                "instruction": combined_instruction,
                "dataset_id": str(dataset.id),
                "mode": "copilot_refine",
                "original_message": message,
                "previous_prompts": [base_instruction] if base_instruction else [],
            },
            requested_by=request.user,
        )

        from apps.dashboards.tasks import generate_dashboard_task

        generate_dashboard_task.delay(str(job.id))

        return Response(
            {
                "job_id": str(job.id),
                "message": "Refinamento em andamento...",
            },
            status=status.HTTP_202_ACCEPTED,
        )
