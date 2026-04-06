"""
apps.users.exceptions
──────────────────────
Handler de erros customizado para o DRF.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler de exceções customizado.
    Formata erros no padrão:
    {
        "error": "ERROR_CODE",
        "message": "Mensagem legível",
        "details": {...}
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = "API_ERROR"
        message = "Ocorreu um erro na requisição."

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "VALIDATION_ERROR"
            message = "Dados inválidos."
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "UNAUTHORIZED"
            message = "Autenticação necessária."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "FORBIDDEN"
            message = "Sem permissão para esta ação."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
            message = "Recurso não encontrado."
        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "RATE_LIMITED"
            message = "Muitas requisições. Tente novamente em instantes."

        response.data = {
            "error": error_code,
            "message": message,
            "details": response.data,
        }

    else:
        # Erro não tratado pelo DRF (500)
        logger.exception("Unhandled exception", exc_info=exc)
        response = Response(
            {
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Erro interno do servidor.",
                "details": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
