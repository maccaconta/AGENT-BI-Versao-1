"""
Agent-BI - Local Fast Settings

Modo de desenvolvimento leve para testes locais sem Docker:
- SQLite no lugar de PostgreSQL
- cache em memória no lugar de Redis
- Celery síncrono/eager
"""
import os
from pathlib import Path

os.environ["DEBUG"] = "True"

from .development import *  # noqa


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Banco local rápido para desenvolvimento
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Sem Redis no modo local rápido
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "agent-bi-local-fast",
    }
}

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Mantém frontend local funcionando sem restrições de CORS
CORS_ALLOW_ALL_ORIGINS = True

# Email de console em dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Prototipo local: desativa Glue/Athena/S3 no fluxo de dados.
USE_AWS_DATA_SERVICES = False

# Redefine REST_FRAMEWORK para garantir que o MockAuth seja o primeiro e evitar problemas de importação
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.mock_auth.LocalFastMockAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.users.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
