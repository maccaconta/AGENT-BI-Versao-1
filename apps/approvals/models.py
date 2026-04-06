"""
apps.approvals.models
──────────────────────
Workflow de aprovação multi-nível e sequencial para Versions.
"""
from django.db import models
from apps.users.models import TimeStampedModel, User
from apps.versions.models import Version


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    IN_PROGRESS = "IN_PROGRESS", "Em Progresso"
    APPROVED = "APPROVED", "Aprovado"
    REJECTED = "REJECTED", "Rejeitado"
    CANCELLED = "CANCELLED", "Cancelado"


class ApprovalStepStatus(models.TextChoices):
    WAITING = "WAITING", "Aguardando"
    ACTIVE = "ACTIVE", "Ativo"
    APPROVED = "APPROVED", "Aprovado"
    REJECTED = "REJECTED", "Rejeitado"
    SKIPPED = "SKIPPED", "Pulado"


class ApprovalWorkflow(TimeStampedModel):
    """
    Workflow de aprovação vinculado a uma Version.
    Controla o fluxo sequencial de aprovação multi-nível.
    """
    version = models.OneToOneField(
        Version,
        on_delete=models.CASCADE,
        related_name="approval_workflow",
        verbose_name="Versão",
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    current_step = models.PositiveIntegerField(default=1, verbose_name="Passo Atual")
    total_steps = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="initiated_workflows",
    )

    notes = models.TextField(blank=True, verbose_name="Notas Gerais")

    class Meta:
        db_table = "approval_workflows"
        verbose_name = "Workflow de Aprovação"
        verbose_name_plural = "Workflows de Aprovação"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Workflow #{self.id} — {self.version} ({self.status})"

    def advance_step(self) -> bool:
        """Avança para o próximo step."""
        if self.current_step >= self.total_steps:
            return False
        self.current_step += 1
        self.save(update_fields=["current_step", "updated_at"])
        return True

    def is_complete(self) -> bool:
        return self.status in [
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
        ]


class ApprovalStep(TimeStampedModel):
    """
    Step individual dentro de um workflow de aprovação.
    Cada step representa um nível de aprovação.
    """
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="Workflow",
    )
    step_number = models.PositiveIntegerField(verbose_name="Número do Step")
    name = models.CharField(max_length=255, verbose_name="Nome do Step")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ApprovalStepStatus.choices,
        default=ApprovalStepStatus.WAITING,
    )

    # Aprovador definido
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_approval_steps",
        verbose_name="Atribuído a",
    )

    # Aprovação/Rejeição
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviewed_steps",
        verbose_name="Revisado Por",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, verbose_name="Comentário")

    # SLA
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "approval_steps"
        verbose_name = "Step de Aprovação"
        verbose_name_plural = "Steps de Aprovação"
        unique_together = [("workflow", "step_number")]
        ordering = ["step_number"]

    def __str__(self):
        return f"Step {self.step_number}: {self.name} ({self.status})"

    def approve(self, user: User, comment: str = "") -> bool:
        """Aprova este step."""
        from django.utils import timezone
        if self.status != ApprovalStepStatus.ACTIVE:
            return False

        self.status = ApprovalStepStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.comment = comment
        self.save()

        # Verificar se workflow está completo
        self._check_workflow_completion()
        return True

    def reject(self, user: User, comment: str = "") -> bool:
        """Rejeita este step (e o workflow inteiro)."""
        from django.utils import timezone
        if self.status != ApprovalStepStatus.ACTIVE:
            return False

        self.status = ApprovalStepStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.comment = comment
        self.save()

        # Rejeitar o workflow
        workflow = self.workflow
        workflow.status = ApprovalStatus.REJECTED
        workflow.completed_at = timezone.now()
        workflow.save()

        # Rejeitar a versão
        self.workflow.version.transition_to("REJECTED", user, comment)
        return True

    def _check_workflow_completion(self):
        """Verifica se todos os steps foram aprovados."""
        from django.utils import timezone
        workflow = self.workflow
        all_steps = workflow.steps.all()

        if workflow.current_step < workflow.total_steps:
            # Avançar para próximo step
            workflow.advance_step()
            next_step = workflow.steps.filter(
                step_number=workflow.current_step
            ).first()
            if next_step:
                next_step.status = ApprovalStepStatus.ACTIVE
                next_step.save()
        else:
            # Todos os steps aprovados
            workflow.status = ApprovalStatus.APPROVED
            workflow.completed_at = timezone.now()
            workflow.save()
            # Aprovar a versão
            self.workflow.version.transition_to(
                "APPROVED", self.reviewed_by
            )
