"""
apps.audit.middleware
──────────────────────
Middleware de auditoria automática de requests HTTP.
"""
import logging
import time

logger = logging.getLogger(__name__)

# Paths que não devem ser auditados (verbosos demais)
EXCLUDED_PATHS = [
    "/api/schema/",
    "/api/docs/",
    "/api/redoc/",
    "/admin/jsi18n/",
    "/static/",
    "/media/",
    "/health/",
]

# Métodos que alteram estado (auditamos apenas estes por padrão)
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware:
    """
    Middleware que registra automaticamente todas as requests que
    modificam estado (POST, PUT, PATCH, DELETE).

    Não audita GET/HEAD para evitar ruído.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        elapsed = time.time() - start_time

        # Auditar apenas requests relevantes
        if self._should_audit(request, response):
            self._log_request(request, response, elapsed)

        return response

    def _should_audit(self, request, response) -> bool:
        """Verifica se a request deve ser auditada."""
        if request.method not in AUDIT_METHODS:
            return False

        for excluded in EXCLUDED_PATHS:
            if request.path.startswith(excluded):
                return False

        return True

    def _log_request(self, request, response, elapsed: float):
        """Registra a request no log de auditoria."""
        try:
            from apps.audit.models import AuditEvent

            user = getattr(request, "user", None)
            tenant = getattr(request, "tenant", None)

            if user and not user.is_authenticated:
                user = None

            action = f"http.{request.method.lower()}"
            payload = {
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed * 1000, 2),
            }

            AuditEvent.log(
                action=action,
                user=user,
                tenant=tenant,
                resource_type="HttpRequest",
                extra=payload,
                request=request,
            )
        except Exception as e:
            logger.warning(f"AuditMiddleware error: {e}")
