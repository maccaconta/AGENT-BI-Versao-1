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
        "NAME": BASE_DIR / "dev.sqlite3",
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

# Habilita Autenticação de Teste/Mock em memória para o frontend
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "apps.users.mock_auth.LocalFastMockAuthentication",
] + REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
