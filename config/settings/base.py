"""
Agent-BI — Base Settings
Configurações compartilhadas entre todos os ambientes.
"""
import os
from datetime import timedelta
from pathlib import Path

from decouple import config, Csv

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Security ─────────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())

# ─── Application Definition ───────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.users",
    "apps.projects",
    "apps.datasets",
    "apps.dashboards",
    "apps.versions",
    "apps.approvals",
    "apps.templates_lib",
    "apps.instructions",
    "apps.ai_engine",
    "apps.infra",
    "apps.governance",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditMiddleware",
    "apps.users.middleware.TenantMiddleware",
]

ROOT_URLCONF = "config.urls"

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="agent_bi_db"),
        "USER": config("DB_USER", default="agent_bi_user"),
        "PASSWORD": config("DB_PASSWORD", default="agent_bi_pass"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Authentication ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ─── Static Files ─────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
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

# ─── JWT ──────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-tenant-slug",
]

# ─── API Docs (Spectacular) ───────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Agent-BI API",
    "DESCRIPTION": "Plataforma Enterprise de Dashboards com IA",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "Autenticação e tokens"},
        {"name": "tenants", "description": "Gerenciamento de tenants"},
        {"name": "users", "description": "Usuários e permissões"},
        {"name": "projects", "description": "Projetos"},
        {"name": "datasets", "description": "Datasets e ingestão"},
        {"name": "dashboards", "description": "Dashboards e geração IA"},
        {"name": "versions", "description": "Versionamento"},
        {"name": "approvals", "description": "Workflow de aprovação"},
        {"name": "templates", "description": "Templates de dashboard e prompt"},
        {"name": "instructions", "description": "Instruções de geração"},
        {"name": "ai", "description": "Engine de IA e agentes"},
        {"name": "infra", "description": "Infraestrutura como código"},
        {"name": "audit", "description": "Auditoria e compliance"},
    ],
}

# ─── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION = config("AWS_REGION", default="us-east-1")
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
S3_ENDPOINT_URL = config("S3_ENDPOINT_URL", default=None)  # MinIO local

# S3 Buckets
S3_DATALAKE_BUCKET = config("S3_DATALAKE_BUCKET", default="agent-bi-datalake-local")
S3_DASHBOARDS_BUCKET = config("S3_DASHBOARDS_BUCKET", default="agent-bi-dashboards-local")
S3_ATHENA_RESULTS_BUCKET = config("S3_ATHENA_RESULTS_BUCKET", default="agent-bi-athena-results-local")

# Feature flags de infraestrutura (permite prototipo local sem AWS data stack)
USE_AWS_DATA_SERVICES = config("USE_AWS_DATA_SERVICES", default=True, cast=bool)
LOCAL_DATA_DIR = config("LOCAL_DATA_DIR", default=str(BASE_DIR / "local_data"))
LOCAL_ANALYTICS_SQLITE_PATH = config(
    "LOCAL_ANALYTICS_SQLITE_PATH",
    default=str(BASE_DIR / "local_data" / "analytics" / "agent_bi_analytics.sqlite"),
)

# Glue
GLUE_DATABASE_PREFIX = config("GLUE_DATABASE_PREFIX", default="agent_bi")
GLUE_CRAWLER_ROLE_ARN = config("GLUE_CRAWLER_ROLE_ARN", default="")

# Athena
ATHENA_WORKGROUP = config("ATHENA_WORKGROUP", default="agent-bi-workgroup")
ATHENA_OUTPUT_LOCATION = config("ATHENA_OUTPUT_LOCATION", default="s3://agent-bi-athena-results/")
ATHENA_QUERY_TIMEOUT = config("ATHENA_QUERY_TIMEOUT", default=300, cast=int)

# Bedrock
BEDROCK_REGION = config("BEDROCK_REGION", default="us-east-1")
BEDROCK_MODEL_ID = config("BEDROCK_MODEL_ID", default="amazon.nova-pro-v1:0")
BEDROCK_MAX_TOKENS = config("BEDROCK_MAX_TOKENS", default=8192, cast=int)
USE_BEDROCK_LLM = config("USE_BEDROCK_LLM", default=True, cast=bool)
BEDROCK_KB_ID = config("BEDROCK_KB_ID", default="")
BEDROCK_KB_MAX_RESULTS = config("BEDROCK_KB_MAX_RESULTS", default=5, cast=int)
USE_BEDROCK_AGENT_RUNTIME = config("USE_BEDROCK_AGENT_RUNTIME", default=False, cast=bool)
BEDROCK_AGENT_ID = config("BEDROCK_AGENT_ID", default="")
BEDROCK_AGENT_ALIAS_ID = config("BEDROCK_AGENT_ALIAS_ID", default="")
BEDROCK_AGENT_ENABLE_TRACE = config("BEDROCK_AGENT_ENABLE_TRACE", default=False, cast=bool)
BEDROCK_AGENT_SESSION_PREFIX = config("BEDROCK_AGENT_SESSION_PREFIX", default="agent-bi")
BEDROCK_AGENT_IDLE_SESSION_TTL_SECONDS = config(
    "BEDROCK_AGENT_IDLE_SESSION_TTL_SECONDS",
    default=900,
    cast=int,
)
BEDROCK_AGENT_FOUNDATION_MODEL = config(
    "BEDROCK_AGENT_FOUNDATION_MODEL",
    default="anthropic.claude-3-5-sonnet-20241022-v2:0",
)

# Step Functions
STEP_FUNCTIONS_REGION = config("STEP_FUNCTIONS_REGION", default="us-east-1")
STEP_FUNCTIONS_ARN = config("STEP_FUNCTIONS_ARN", default="")

# Cognito
COGNITO_REGION = config("COGNITO_REGION", default="us-east-1")
COGNITO_USER_POOL_ID = config("COGNITO_USER_POOL_ID", default="")
COGNITO_APP_CLIENT_ID = config("COGNITO_APP_CLIENT_ID", default="")
COGNITO_APP_CLIENT_SECRET = config("COGNITO_APP_CLIENT_SECRET", default="")

# CloudFront
CLOUDFRONT_DOMAIN = config("CLOUDFRONT_DOMAIN", default="")
CLOUDFRONT_DISTRIBUTION_ID = config("CLOUDFRONT_DISTRIBUTION_ID", default="")

# ─── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hora max por task

# ─── AI Settings ──────────────────────────────────────────────────────────────
AI_MAX_ITERATIONS = config("AI_MAX_ITERATIONS", default=3, cast=int)
AI_MIN_SCORE_THRESHOLD = config("AI_MIN_SCORE_THRESHOLD", default=0.8, cast=float)

# ─── File Upload ──────────────────────────────────────────────────────────────
MAX_DATASET_SIZE_MB = config("MAX_DATASET_SIZE_MB", default=500, cast=int)
MAX_FILE_ROWS = config("MAX_FILE_ROWS", default=1_000_000, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_DATASET_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_DATASET_SIZE_MB * 1024 * 1024

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
