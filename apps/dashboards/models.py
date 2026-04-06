"""
apps.dashboards.models
───────────────────────
Dashboard: resultado da geração com IA, publicado via CloudFront.
"""
from django.db import models
from apps.users.models import TimeStampedModel, User
from apps.projects.models import Project


class DashboardStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    PUBLISHED = "PUBLISHED", "Publicado"
    ARCHIVED = "ARCHIVED", "Arquivado"


class Dashboard(TimeStampedModel):
    """
    Dashboard gerado por IA e publicado via CloudFront.
    Cada Dashboard possui múltiplas Versions.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="dashboards",
        verbose_name="Projeto",
    )
    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=DashboardStatus.choices,
        default=DashboardStatus.DRAFT,
    )

    # Instrução original que gerou o dashboard
    instruction = models.ForeignKey(
        "instructions.Instruction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dashboards",
        verbose_name="Instrução",
    )

    # Template usado
    template = models.ForeignKey(
        "templates_lib.DashboardTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_dashboards",
        verbose_name="Template",
    )

    # Versão atual aprovada/publicada
    current_version = models.ForeignKey(
        "versions.Version",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Versão Atual",
    )

    # Publicação
    cloudfront_url = models.URLField(blank=True, verbose_name="URL CloudFront")
    s3_published_path = models.CharField(max_length=1000, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="published_dashboards",
    )

    # Configuração
    config = models.JSONField(
        default=dict, blank=True,
        verbose_name="Configuração",
        help_text="Configurações de layout, tema, filtros",
    )
    tags = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=False, verbose_name="Público")

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_dashboards",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="updated_dashboards",
    )

    class Meta:
        db_table = "dashboards"
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboards"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    @property
    def version_count(self):
        return self.versions.filter(is_deleted=False).count()

    @property
    def is_published(self):
        return self.status == DashboardStatus.PUBLISHED


class GenerationJob(TimeStampedModel):
    """
    Job de geração de Dashboard via IA.
    Rastreia o status da execução no Step Functions.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        RUNNING = "RUNNING", "Executando"
        SUCCEEDED = "SUCCEEDED", "Concluído"
        FAILED = "FAILED", "Falhou"
        CANCELLED = "CANCELLED", "Cancelado"

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="generation_jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Step Functions
    step_functions_execution_arn = models.CharField(max_length=500, blank=True)
    step_functions_execution_name = models.CharField(max_length=255, blank=True)

    # Input / Output
    input_payload = models.JSONField(default=dict)
    output_payload = models.JSONField(default=dict, blank=True)

    # Progresso
    current_iteration = models.PositiveIntegerField(default=0)
    max_iterations = models.PositiveIntegerField(default=3)
    final_score = models.FloatField(null=True, blank=True)

    # Erro
    error_details = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name="generation_jobs",
    )

    class Meta:
        db_table = "generation_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Job {self.id} — {self.dashboard.name} ({self.status})"
