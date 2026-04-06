from django.apps import AppConfig


class VersionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.versions"
    verbose_name = "Versões"


class ApprovalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.approvals"
    verbose_name = "Aprovações"


class TemplatesLibConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.templates_lib"
    verbose_name = "Templates"


class InstructionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.instructions"
    verbose_name = "Instruções"


class AIEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_engine"
    verbose_name = "AI Engine"


class InfraConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.infra"
    verbose_name = "Infraestrutura"


class GovernanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.governance"
    verbose_name = "Governança"


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Auditoria"

    def ready(self):
        import apps.audit.signals  # noqa: F401
