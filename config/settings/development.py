"""
Agent-BI — Development Settings
"""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

# ─── Dev Database (pode usar DATABASE_URL do .env) ────────────────────────────
# Já configurado via base.py + decouple

# ─── S3 Local (MinIO) ─────────────────────────────────────────────────────────
# S3_ENDPOINT_URL definido via .env aponta para MinIO

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Debug Toolbar ────────────────────────────────────────────────────────────
INSTALLED_APPS += ["django_extensions"]  # noqa

# ─── CORS dev (permissivo) ────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ─── Swagger UI ───────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = True  # noqa

# ─── Cache em memória para dev ────────────────────────────────────────────────
# Mantém Redis do base.py para consistência

# ─── Django Extensions ────────────────────────────────────────────────────────
SHELL_PLUS_PRINT_SQL = True
