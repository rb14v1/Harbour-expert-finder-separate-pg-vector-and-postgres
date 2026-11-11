"""
Base settings shared by all environments.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-secret-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # local apps
    "apps.accounts",
    "apps.common",
    "apps.directory",
    "apps.knowledge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ---------------------------------------------------------------------------
# Database
#
# Real deployments (docker-compose / prod) use plain Postgres - NO pgvector
# extension. Unlike the earlier "AI apps" in this workspace, this app keeps
# all relational data in Postgres and stores embeddings in a completely
# separate vector database (Qdrant - see apps/common/qdrant_store.py). There
# is no shared transaction between the two; see the README for the
# consistency tradeoffs this implies.
#
# DEV-ONLY OVERRIDE: when USE_SQLITE=True is set in the environment, fall
# back to SQLite so `manage.py check`, `makemigrations` and `test` can run on
# a machine with no Postgres install available (e.g. this sandbox). Combined
# with Qdrant's ":memory:" embedded mode (also gated on this flag - see
# qdrant_store.py), the whole app runs with zero external services. Never
# set USE_SQLITE in docker-compose/production.
# ---------------------------------------------------------------------------
USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "dev-sqlite.db",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="expert_finder"),
            "USER": config("POSTGRES_USER", default="expert_finder"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="expert_finder"),
            "HOST": config("POSTGRES_HOST", default="localhost"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/min",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Vector store (Qdrant) - apps/common/qdrant_store.py
#
# Dev/test mode: when QDRANT_URL is unset, qdrant_store constructs an
# in-process QdrantClient(location=":memory:") - the real Qdrant engine
# running embedded, no server needed. This is the equivalent of USE_SQLITE
# for the vector side of this app's two-database architecture.
#
# Real mode: set QDRANT_URL (e.g. http://localhost:6333) to talk to an
# actual Qdrant server, as docker-compose.yml does for the `backend` service.
# ---------------------------------------------------------------------------
QDRANT_URL = config("QDRANT_URL", default="")

# ---------------------------------------------------------------------------
# AI / embeddings (apps/common/ai.py)
#
# Without OPENAI_API_KEY set, get_embedding() falls back to a deterministic,
# no-network stub so the whole embed -> store -> similarity search pipeline
# is fully testable without any API key or cost. Set OPENAI_API_KEY to
# switch to real OpenAI calls.
# ---------------------------------------------------------------------------
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-large")
OPENAI_CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-5.6-sol")  # unused by this app today; kept for consistency with sibling apps

# text-embedding-3-large is natively 3072-dimensional but supports OpenAI's
# `dimensions` param to shorten the vector. 1536 keeps Qdrant's collection
# size manageable while still using the large model's quality. This value
# must exactly match the Qdrant collection's configured vector size (see
# qdrant_store.py) - Qdrant rejects vectors of any other length.
EMBEDDING_DIMENSIONS = config("OPENAI_EMBEDDING_DIMENSIONS", default=1536, cast=int)

# Default number of results returned by /api/search/knowledge/ and
# /api/search/experts/ when the request doesn't override via ?top_k=.
SEARCH_TOP_K = config("SEARCH_TOP_K", default=5, cast=int)
