"""
apps.dashboards.tasks
Task Celery unificada com o agente incremental de BI.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=1,
    name="dashboards.generate_dashboard",
    time_limit=1800,
)
def generate_dashboard_task(self, job_id: str):
    """
    Executa a geracao de dashboard usando o mesmo agente incremental
    consumido pelo endpoint /api/v1/copilot/generate.
    """
    from apps.dashboards.models import GenerationJob

    try:
        job = GenerationJob.objects.select_related(
            "dashboard",
            "dashboard__project",
            "dashboard__current_version",
            "requested_by",
        ).get(id=job_id)
    except GenerationJob.DoesNotExist:
        logger.error("GenerationJob %s nao encontrado.", job_id)
        return

    logger.info("[GenerationTask] Iniciando job %s", job_id)

    job.status = GenerationJob.Status.RUNNING
    job.started_at = timezone.now()
    job.current_iteration = 1
    job.save(update_fields=["status", "started_at", "current_iteration", "updated_at"])

    try:
        from apps.ai_engine.services.incremental_dashboard_agent import IncrementalDashboardAgentService
        from apps.datasets.models import Dataset

        dashboard = job.dashboard
        input_payload = job.input_payload or {}
        instruction = input_payload.get("instruction") or "Analise os dados e evolua o dashboard existente."
        dataset_id = input_payload.get("dataset_id")
        template_id = input_payload.get("template_id")

        dataset = None
        if dataset_id:
            dataset = Dataset.objects.filter(
                id=dataset_id,
                project=dashboard.project,
                is_deleted=False,
            ).first()

        template_hints = ""
        if template_id:
            from apps.templates_lib.models import DashboardTemplate

            template = DashboardTemplate.objects.filter(id=template_id).first()
            if template:
                template_hints = template.prompt_hints or ""

        service = IncrementalDashboardAgentService()
        serialized_datasets = service._serialize_project_datasets(dashboard.project)
        if dataset:
            serialized_datasets = [
                item for item in serialized_datasets if item.get("id") == str(dataset.id)
            ]

        result = service.generate(
            {
                "dashboard_id": str(dashboard.id),
                "project_id": str(dashboard.project_id),
                "dashboardName": dashboard.name,
                "reportTitle": dashboard.name,
                "reportDescription": dashboard.description,
                "templatePrompt": template_hints,
                "currentUserPrompt": instruction,
                "currentVersion": (
                    f"v{dashboard.current_version.version_number}"
                    if dashboard.current_version
                    else ""
                ),
                "currentDashboardState": (
                    dashboard.current_version.state
                    if dashboard.current_version
                    else dashboard.status
                ),
                "datasets": serialized_datasets,
                "semanticRelationships": input_payload.get("semantic_relationships", []),
                "reportMetadata": {
                    "job_id": str(job.id),
                    "mode": input_payload.get("mode", "job_generation"),
                    "dataset_id": str(dataset.id) if dataset else "",
                },
                "previousUserPrompts": input_payload.get("previous_prompts", []),
            },
            request_user=job.requested_by,
            save_version=True,
        )

        dashboard.refresh_from_db(fields=["current_version", "updated_at"])
        version = dashboard.current_version
        sql_validation = result.get("sqlValidation", {})
        validation_status = sql_validation.get("status")
        computed_score = 1.0 if validation_status == "validated" else 0.75

        job.status = GenerationJob.Status.SUCCEEDED
        job.finished_at = timezone.now()
        job.final_score = computed_score
        job.output_payload = {
            "version_id": str(version.id) if version else "",
            "version_number": version.version_number if version else None,
            "score": computed_score,
            "iterations": 1,
            "sql_validation": sql_validation,
            "analysis_intent": result.get("analysisIntent", {}),
            "dashboard_plan": result.get("dashboardPlan", {}),
        }
        job.save()

        logger.info(
            "[GenerationTask] Job %s concluido. Version %s, score=%.3f",
            job_id,
            getattr(version, "version_number", "n/a"),
            computed_score,
        )

        from apps.audit.signals import audit_event

        audit_event.send(
            sender=generate_dashboard_task,
            action="dashboard.generation_completed",
            resource_type="Dashboard",
            resource_id=dashboard.id,
            extra={
                "version_id": str(version.id) if version else "",
                "score": computed_score,
                "iterations": 1,
                "sql_validation_status": validation_status,
            },
        )

        if version:
            _notify_eventbridge(job, version)

    except Exception as exc:
        logger.error("[GenerationTask] Erro no job %s: %s", job_id, exc)
        job.status = GenerationJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error_details = str(exc)
        job.save(update_fields=["status", "finished_at", "error_details", "updated_at"])
        raise


def _notify_eventbridge(job, version):
    """Envia evento para Amazon EventBridge quando disponivel."""
    try:
        import boto3
        from django.conf import settings

        eb = boto3.client("events", region_name=settings.AWS_REGION)
        eb.put_events(
            Entries=[{
                "Source": "agent-bi.dashboard",
                "DetailType": "DashboardGenerated",
                "Detail": str({
                    "job_id": str(job.id),
                    "dashboard_id": str(job.dashboard.id),
                    "version_id": str(version.id),
                    "score": version.ai_score or job.final_score,
                }),
            }]
        )
    except Exception as exc:
        logger.warning("EventBridge notification failed: %s", exc)
