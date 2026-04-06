"""
apps.instructions.models + apps.templates_lib.models
───────────────────────────────────────────────────
Instruções de geração e templates de dashboard/prompt.
"""
from django.db import models
from apps.users.models import TimeStampedModel, User
from apps.projects.models import Project


# ─── Instructions ─────────────────────────────────────────────────────────────

class Instruction(TimeStampedModel):
    """
    Instrução em linguagem natural para geração de dashboard.
    Versionada e reutilizável entre dashboards.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="instructions",
        null=True, blank=True,
    )
    name = models.CharField(max_length=255)
    content = models.TextField(verbose_name="Instrução")
    description = models.TextField(blank=True)
    is_global = models.BooleanField(
        default=False,
        help_text="Instrução disponível para todos os projetos do tenant",
    )
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "instructions"
        db_table = "instructions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class InstructionVersion(TimeStampedModel):
    """Histórico de versões de uma instrução."""
    instruction = models.ForeignKey(
        Instruction,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    content = models.TextField()
    change_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "instructions"
        db_table = "instruction_versions"
        unique_together = [("instruction", "version_number")]
        ordering = ["-version_number"]


# ─── Templates ────────────────────────────────────────────────────────────────

class DashboardTemplate(TimeStampedModel):
    """
    Template de layout para dashboards.
    Define estrutura, componentes e estilo visual.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("FINANCIAL", "Financeiro"),
            ("SALES", "Vendas"),
            ("MARKETING", "Marketing"),
            ("OPERATIONS", "Operações"),
            ("HR", "RH"),
            ("EXECUTIVE", "Executivo"),
            ("CUSTOM", "Customizado"),
        ],
        default="CUSTOM",
    )

    # Conteúdo do template
    html_template = models.TextField(
        blank=True,
        verbose_name="Template HTML Base",
    )
    prompt_hints = models.TextField(
        blank=True,
        verbose_name="Dicas para o Generator Agent",
        help_text="Instruções específicas enviadas ao Generator para seguir este template",
    )
    css_theme = models.TextField(blank=True, verbose_name="CSS do Tema")
    config = models.JSONField(default=dict, blank=True)

    # S3
    s3_path = models.CharField(max_length=1000, blank=True)

    # Visibilidade
    is_public = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default="1.0.0")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "templates_lib"
        db_table = "dashboard_templates"
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class PromptTemplate(TimeStampedModel):
    """
    Template de prompt para reutilização.
    Prompts pré-configurados para casos de uso específicos.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content = models.TextField(verbose_name="Template do Prompt")
    category = models.CharField(max_length=50, blank=True)
    variables = models.JSONField(
        default=list, blank=True,
        help_text="Variáveis interpoláveis: [{name, description, required}]",
    )
    is_public = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default="1.0.0")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "templates_lib"
        db_table = "prompt_templates"
        ordering = ["category", "name"]

    def render(self, variables: dict) -> str:
        """Renderiza o template substituindo variáveis."""
        content = self.content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content


# ─── Infra Models ─────────────────────────────────────────────────────────────

class InfraConfig(TimeStampedModel):
    """Configuração de infraestrutura gerada pelo Infra Agent."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="infra_configs",
    )
    name = models.CharField(max_length=255, default="main")
    terraform_files = models.JSONField(
        default=dict,
        verbose_name="Arquivos Terraform",
    )
    estimated_resources = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="applied_infra_configs",
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "infra"
        db_table = "infra_configs"
        ordering = ["-created_at"]


class TerraformPlan(TimeStampedModel):
    """
    Plano de execução Terraform (output de terraform plan).
    Requer aprovação antes de apply.
    """
    class Status(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Aguardando Revisão"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Rejeitado"
        APPLYING = "APPLYING", "Aplicando"
        APPLIED = "APPLIED", "Aplicado"
        FAILED = "FAILED", "Falhou"

    infra_config = models.ForeignKey(
        InfraConfig,
        on_delete=models.CASCADE,
        related_name="terraform_plans",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    plan_output = models.TextField(blank=True, verbose_name="Output do Plan")
    resources_to_add = models.IntegerField(default=0)
    resources_to_change = models.IntegerField(default=0)
    resources_to_destroy = models.IntegerField(default=0)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_terraform_plans",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = "infra"
        db_table = "terraform_plans"
        ordering = ["-created_at"]
