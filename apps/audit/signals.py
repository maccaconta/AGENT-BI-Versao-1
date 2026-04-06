"""
apps.audit.signals
───────────────────
Signals para emissão de eventos de auditoria.
"""
import logging
from django.dispatch import Signal, receiver

logger = logging.getLogger(__name__)

# Signal customizado de auditoria
audit_event = Signal()


@receiver(audit_event)
def handle_audit_event(
    sender,
    action: str,
    user=None,
    tenant=None,
    resource_type: str = "",
    resource_id=None,
    extra: dict = None,
    request=None,
    **kwargs,
):
    """
    Recebe signals de auditoria e persiste no banco.
    Usa try/except para nunca quebrar o fluxo principal.
    """
    try:
        from apps.audit.models import AuditEvent
        AuditEvent.log(
            action=action,
            user=user,
            tenant=tenant,
            resource_type=resource_type,
            resource_id=resource_id,
            extra=extra,
            request=request,
        )
    except Exception as e:
        logger.error(f"Falha ao persistir AuditEvent '{action}': {e}")
