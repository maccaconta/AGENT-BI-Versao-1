"""
apps.projects.models
─────────────────────
Project: unidade central do sistema Agent-BI.
"""
import uuid
from django.db import models
from apps.users.models import TimeStampedModel, Tenant, User, RoleChoices


class DataDomain(TimeStampedModel):
    """
    Domínio de Dados (Data Mesh): Agrupamento lógico de projetos por área de negócio.
    Ex: Financeiro, RH, Varejo, Operações.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="domains",
        verbose_name="Tenant",
    )
    name = models.CharField(max_length=100, verbose_name="Nome do Domínio")
    description = models.TextField(blank=True, verbose_name="Descrição do Domínio")
    icon = models.CharField(max_length=50, default="Database", help_text="Ícone Lucide")
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_domains",
        verbose_name="Dono do Domínio (Data Product Manager)"
    )

    class Meta:
        db_table = "data_domains"
        unique_together = [("tenant", "name")]
        verbose_name = "Domínio de Dados"
        verbose_name_plural = "Domínios de Dados"

    def __str__(self):
        return f"{self.name} | {self.tenant.slug}"


class ProjectStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    ARCHIVED = "ARCHIVED", "Arquivado"
    SUSPENDED = "SUSPENDED", "Suspenso"


class Project(TimeStampedModel):
    """
    Projeto: agrupa datasets, dashboards, pipelines e infraestrutura.
    É a unidade central do sistema.
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="Tenant",
    )
    domain = models.ForeignKey(
        DataDomain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="Domínio de Dados"
    )
    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    domain_data_owner = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Domain Data Owner",
    )
    data_confidentiality = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Confidencialidade dos Dados",
    )
    crawler_frequency = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Frequência do Crawler",
    )
    intake_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadados de Intake",
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.ACTIVE,
    )
    analysis_max_rows = models.PositiveIntegerField(
        default=5000,
        verbose_name="Limite de Linhas para Análise IA",
        help_text="Máximo de linhas processadas pelo Agente de Estatística (Pandas) para garantir performance."
    )
    ai_temperature = models.FloatField(
        default=0.3,
        verbose_name="Temperatura da IA",
        help_text="Calibração do nível de criatividade da IA (0.0 a 1.0)."
    )

    specialist_prompt = models.ForeignKey(
        "templates_lib.PromptTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="Especialista de Domínio",
        help_text="Persona cognitiva selecionada para guiar as análises e o draft deste projeto."
    )

    # AWS Resources
    s3_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Caminho S3",
        help_text="Prefixo S3 do projeto no Data Lake",
    )
    glue_database = models.CharField(
        max_length=255, blank=True, verbose_name="Glue Database"
    )
    athena_workgroup = models.CharField(
        max_length=255, blank=True, verbose_name="Athena Workgroup"
    )

    # Settings
    default_dataset = models.ForeignKey(
        "datasets.Dataset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Dataset Padrão",
    )
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
        verbose_name="Criado Por",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_projects",
    )

    class Meta:
        db_table = "projects"
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        ordering = ["-created_at"]
        unique_together = [("tenant", "name")]

    def __str__(self):
        return f"{self.name} ({self.tenant.slug})"

    def save(self, *args, **kwargs):
        # Auto-gerar paths AWS baseados no tenant + project slug
        if not self.s3_path and self.tenant:
            project_slug = self.name.lower().replace(" ", "-")[:50]
            s3_prefix = self.tenant.s3_prefix or "agent-bi-local"
            self.s3_path = f"{s3_prefix}/{project_slug}"

        if not self.glue_database and self.tenant:
            project_slug = self.name.lower().replace(" ", "_")[:50]
            glue_prefix = self.tenant.glue_database_prefix or "agent_bi_local"
            self.glue_database = f"{glue_prefix}_{project_slug}"

        if not self.athena_workgroup and self.tenant:
            self.athena_workgroup = self.tenant.athena_workgroup or "primary"

        super().save(*args, **kwargs)

    @property
    def dataset_count(self):
        return self.datasets.filter(is_deleted=False).count()

    @property
    def dashboard_count(self):
        return self.dashboards.filter(is_deleted=False).count()


class ProjectMember(TimeStampedModel):
    """
    Membro específico de um projeto com role project-level.
    Permite granularidade abaixo do nível de tenant.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.VIEWER,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "project_members"
        unique_together = [("project", "user")]
        ordering = ["project", "role"]

    def __str__(self):
        return f"{self.user.email} → {self.project.name} ({self.role})"
