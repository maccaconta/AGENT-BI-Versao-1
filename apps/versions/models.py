"""
apps.versions.models
─────────────────────
Version: snapshot completo e imutável de um Dashboard.
"""
from django.db import models
from apps.users.models import TimeStampedModel, User
from apps.dashboards.models import Dashboard


class VersionState(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    CANDIDATE = "CANDIDATE", "Candidato"
    UNDER_REVIEW = "UNDER_REVIEW", "Em Revisão"
    APPROVED = "APPROVED", "Aprovado"
    BLUEPRINT = "BLUEPRINT", "Blueprint"
    ARCHIVED = "ARCHIVED", "Arquivado"
    REJECTED = "REJECTED", "Rejeitado"


class Version(TimeStampedModel):
    """
    Snapshot completo e imutável de um Dashboard.
    Cada iteração de melhoria IA gera uma nova versão.
    """
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Dashboard",
    )
    version_number = models.PositiveIntegerField(verbose_name="Número da Versão")
    state = models.CharField(
        max_length=20,
        choices=VersionState.choices,
        default=VersionState.DRAFT,
        verbose_name="Estado",
    )

    # Snapshot HTML
    html_s3_path = models.CharField(
        max_length=1000, blank=True,
        verbose_name="Path HTML no S3",
    )
    html_preview_url = models.URLField(blank=True, verbose_name="URL Preview")

    # Geração IA
    sql_queries = models.JSONField(
        default=list, blank=True,
        verbose_name="Queries SQL",
        help_text="Lista de queries Athena geradas pela IA",
    )
    ai_insights = models.TextField(blank=True, verbose_name="Insights IA")
    full_prompt = models.TextField(
        blank=True, verbose_name="Prompt Completo",
        help_text="Prompt completo enviado à IA (para reprodutibilidade)",
    )
    ai_score = models.FloatField(
        null=True, blank=True,
        verbose_name="Score IA",
        help_text="Score do Critic Agent (0.0 a 1.0)",
    )
    critic_feedback = models.TextField(blank=True, verbose_name="Feedback do Critic")
    iterations = models.PositiveIntegerField(
        default=1, verbose_name="Iterações IA"
    )

    # Instrução e template no momento da geração
    instruction_snapshot = models.JSONField(
        default=dict, blank=True,
        verbose_name="Snapshot da Instrução",
        help_text="Cópia da instrução usada na geração",
    )
    template_snapshot = models.JSONField(
        default=dict, blank=True,
        verbose_name="Snapshot do Template",
    )
    dataset_snapshot = models.JSONField(
        default=dict, blank=True,
        verbose_name="Snapshot do Dataset",
        help_text="Schema e metadata do dataset no momento da geração",
    )

    # Infraestrutura associada
    infra_config = models.ForeignKey(
        "infra.InfraConfig",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="versions",
        verbose_name="Config Infra",
    )

    # Aprovação
    submitted_for_review_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_versions",
    )
    rejection_reason = models.TextField(blank=True)

    # Notas
    change_summary = models.TextField(
        blank=True, verbose_name="Resumo de Mudanças"
    )

    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_versions",
    )

    class Meta:
        db_table = "versions"
        verbose_name = "Versão"
        verbose_name_plural = "Versões"
        unique_together = [("dashboard", "version_number")]
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.dashboard.name} v{self.version_number} ({self.state})"

    @property
    def is_approved(self):
        return self.state == VersionState.APPROVED

    @property
    def is_editable(self):
        return self.state in [VersionState.DRAFT, VersionState.CANDIDATE]

    def transition_to(self, new_state: str, user: User, reason: str = "") -> bool:
        """
        Máquina de estados das versões.
        Valida transições permitidas.
        """
        from django.utils import timezone

        allowed_transitions = {
            VersionState.DRAFT: [VersionState.CANDIDATE, VersionState.ARCHIVED],
            VersionState.CANDIDATE: [
                VersionState.UNDER_REVIEW,
                VersionState.DRAFT,
                VersionState.ARCHIVED,
            ],
            VersionState.UNDER_REVIEW: [
                VersionState.APPROVED,
                VersionState.REJECTED,
                VersionState.CANDIDATE,
            ],
            VersionState.APPROVED: [VersionState.BLUEPRINT, VersionState.ARCHIVED],
            VersionState.BLUEPRINT: [VersionState.ARCHIVED],
            VersionState.REJECTED: [VersionState.DRAFT, VersionState.ARCHIVED],
        }

        if new_state not in allowed_transitions.get(self.state, []):
            return False

        old_state = self.state
        self.state = new_state

        if new_state == VersionState.UNDER_REVIEW:
            self.submitted_for_review_at = timezone.now()
        elif new_state == VersionState.APPROVED:
            self.approved_at = timezone.now()
            self.approved_by = user
        elif new_state == VersionState.REJECTED:
            self.rejection_reason = reason

        self.save()

        # Emitir evento de auditoria
        from apps.audit.signals import audit_event
        audit_event.send(
            sender=self.__class__,
            action=f"version.state.{new_state.lower()}",
            user=user,
            resource_type="Version",
            resource_id=self.id,
            extra={"old_state": old_state, "new_state": new_state, "reason": reason},
        )

        return True


class VersionIterationLog(TimeStampedModel):
    """Log de cada iteração do loop IA para uma versão."""
    version = models.ForeignKey(
        Version,
        on_delete=models.CASCADE,
        related_name="iteration_logs",
    )
    iteration_number = models.PositiveIntegerField()
    generator_prompt = models.TextField(blank=True)
    generator_response = models.TextField(blank=True)
    critic_prompt = models.TextField(blank=True)
    critic_response = models.TextField(blank=True)
    score = models.FloatField(null=True)
    feedback = models.TextField(blank=True)
    execution_time_seconds = models.FloatField(null=True)
    athena_queries_executed = models.JSONField(default=list)

    class Meta:
        db_table = "version_iteration_logs"
        ordering = ["iteration_number"]
