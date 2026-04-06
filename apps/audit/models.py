"""
apps.audit.models
──────────────────
AuditEvent: registro imutável e auditável de todas as ações do sistema.
"""
from django.db import models
from apps.users.models import TimeStampedModel


class AuditEventAction(models.TextChoices):
    # Auth
    USER_REGISTERED = "user.registered", "Usuário registrado"
    USER_LOGIN = "user.login", "Login"
    USER_LOGOUT = "user.logout", "Logout"
    USER_PASSWORD_CHANGED = "user.password_changed", "Senha alterada"

    # Tenant
    TENANT_CREATED = "tenant.created", "Tenant criado"
    TENANT_MEMBER_INVITED = "tenant.member_invited", "Membro convidado"
    TENANT_MEMBER_ROLE_CHANGED = "tenant.member_role_changed", "Role alterado"

    # Project
    PROJECT_CREATED = "project.created", "Projeto criado"
    PROJECT_UPDATED = "project.updated", "Projeto atualizado"
    PROJECT_ARCHIVED = "project.archived", "Projeto arquivado"

    # Dataset
    DATASET_UPLOADED = "dataset.uploaded", "Dataset enviado"
    DATASET_PROCESSED = "dataset.processed", "Dataset processado"
    DATASET_ERROR = "dataset.error", "Erro no dataset"

    # Dashboard
    DASHBOARD_CREATED = "dashboard.created", "Dashboard criado"
    DASHBOARD_GENERATION_STARTED = "dashboard.generation_started", "Geração iniciada"
    DASHBOARD_GENERATION_COMPLETED = "dashboard.generation_completed", "Geração concluída"
    DASHBOARD_PUBLISHED = "dashboard.published", "Dashboard publicado"

    # Version
    VERSION_CREATED = "version.created", "Versão criada"
    VERSION_SUBMITTED = "version.submitted", "Versão submetida"
    VERSION_APPROVED = "version.state.approved", "Versão aprovada"
    VERSION_REJECTED = "version.state.rejected", "Versão rejeitada"
    VERSION_ARCHIVED = "version.state.archived", "Versão arquivada"

    # Approval
    APPROVAL_STARTED = "approval.started", "Aprovação iniciada"
    APPROVAL_STEP_APPROVED = "approval.step.approved", "Step aprovado"
    APPROVAL_STEP_REJECTED = "approval.step.rejected", "Step rejeitado"

    # AI
    AI_GENERATION_STARTED = "ai.generation_started", "Geração IA iniciada"
    AI_GENERATION_COMPLETED = "ai.generation_completed", "Geração IA concluída"
    AI_CRITIC_SCORED = "ai.critic_scored", "Score Critic IA"

    # Infra
    INFRA_PLAN_GENERATED = "infra.plan_generated", "Plano Terraform gerado"
    INFRA_PLAN_APPROVED = "infra.plan_approved", "Plano Terraform aprovado"
    INFRA_APPLIED = "infra.applied", "Infra aplicada"


class AuditEvent(models.Model):
    """
    Registro imutável de eventos auditáveis.
    Nunca deve ser editado ou deletado.
    """
    import uuid as _uuid

    id = models.UUIDField(primary_key=True, default=_uuid.uuid4, editable=False)

    # Contexto
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.CharField(max_length=255, blank=True)

    # Evento
    action = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Ação",
    )
    resource_type = models.CharField(
        max_length=100, blank=True,
        verbose_name="Tipo do Recurso",
    )
    resource_id = models.CharField(
        max_length=255, blank=True,
        verbose_name="ID do Recurso",
        db_index=True,
    )

    # Payload completo
    payload = models.JSONField(
        default=dict,
        verbose_name="Payload",
        help_text="Dados completos do evento",
    )

    # HTTP context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)

    # Timestamp imutável
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_events"
        verbose_name = "Evento de Auditoria"
        verbose_name_plural = "Eventos de Auditoria"
        ordering = ["-timestamp"]
        # Nunca permitir update/delete via Django admin
        default_permissions = ("view",)

    def __str__(self):
        return f"[{self.timestamp}] {self.action} by {self.user_email}"

    def save(self, *args, **kwargs):
        """Garante que events existentes não sejam modificados."""
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditEvent é imutável. Não pode ser editado.")
        super().save(*args, **kwargs)

    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        tenant=None,
        resource_type: str = "",
        resource_id=None,
        extra: dict = None,
        request=None,
    ) -> "AuditEvent":
        """Factory method para criar eventos de auditoria."""
        payload = extra or {}

        event = cls(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            payload=payload,
        )

        if user:
            event.user_id = user.id if hasattr(user, "id") else None
            event.user_email = user.email if hasattr(user, "email") else ""

        if tenant:
            event.tenant_id = tenant.id if hasattr(tenant, "id") else None

        if request:
            event.ip_address = cls._get_client_ip(request)
            event.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
            event.request_method = request.method
            event.request_path = request.path[:500]

        event.save()
        return event

    @staticmethod
    def _get_client_ip(request) -> str:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

class ExecutionTrace(models.Model):
    """
    Rastreamento técnico granulado de execuções de longa duração (Ingestão/IA).
    Focado em performance e transparência técnica (Tracer/HUD).
    """
    trace_id = models.UUIDField(db_index=True, help_text="ID para agrupar passos de uma mesma execução")
    job_type = models.CharField(max_length=50, db_index=True) # INGESTION, AI_GENERATION
    step_name = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    
    # Métricas de Performance e Consumo
    duration_ms = models.IntegerField(default=0, help_text="Duração da etapa em milissegundos")
    input_tokens = models.IntegerField(default=0, help_text="Tokens enviados (se IA)")
    output_tokens = models.IntegerField(default=0, help_text="Tokens recebidos (se IA)")
    
    status = models.CharField(max_length=20, default="SUCCESS") # SUCCESS, WARNING, ERROR
    
    # Payload detalhado (Prompt, Resposta Bruta, etc)
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_execution_traces"
        verbose_name = "Trace de Execução"
        verbose_name_plural = "Traces de Execução"
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.job_type}] {self.step_name} ({self.duration_ms}ms)"
