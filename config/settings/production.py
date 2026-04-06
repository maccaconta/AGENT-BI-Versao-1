"""
Agent-BI — Production Settings
"""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from decouple import config
from .base import *  # noqa

DEBUG = False

# ─── Security ─────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ─── Database (produção: RDS Multi-AZ) ───────────────────────────────────────
DATABASES["default"]["CONN_MAX_AGE"] = 300  # noqa
DATABASES["default"]["OPTIONS"] = {  # noqa
    "connect_timeout": 10,
    "sslmode": "require",
}

# ─── Email (SES) ──────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "email-smtp.us-east-1.amazonaws.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("SES_SMTP_USER", default="")
EMAIL_HOST_PASSWORD = config("SES_SMTP_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("EMAIL_FROM", default="noreply@agent-bi.com")

# ─── Sentry ───────────────────────────────────────────────────────────────────
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )

# ─── Logging (CloudWatch) ─────────────────────────────────────────────────────
LOGGING["handlers"]["cloudwatch"] = {  # noqa
    "class": "logging.StreamHandler",
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["cloudwatch"]  # noqa
