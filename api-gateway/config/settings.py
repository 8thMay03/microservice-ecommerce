from decouple import config

SECRET_KEY = config("SECRET_KEY", default="django-insecure-gateway-dev-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_prometheus",
    "proxy",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

# No database needed for gateway — it's stateless
DATABASES = {}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Gateway is stateless — no DB, no auth.User, no contenttypes.
    # Without this, DRF tries to import AnonymousUser which pulls in
    # django.contrib.contenttypes and crashes because it's not installed.
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
}

CORS_ALLOW_ALL_ORIGINS = True
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Structured Logging (visible in Loki) ─────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "service": "api-gateway", "logger": "%(name)s", "message": "%(message)s"}',
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "proxy": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ── Downstream service registry ───────────────────────────────────────────────
SERVICE_REGISTRY = {
    "customers":     config("CUSTOMER_SERVICE_URL",    default="http://customer-service:8000"),
    "books":         config("BOOK_SERVICE_URL",         default="http://book-service:8000"),
    "catalog":       config("CATALOG_SERVICE_URL",      default="http://catalog-service:8000"),
    "cart":          config("CART_SERVICE_URL",          default="http://cart-service:8000"),
    "orders":        config("ORDER_SERVICE_URL",         default="http://order-service:8000"),
    "payments":      config("PAY_SERVICE_URL",           default="http://pay-service:8000"),
    "shipments":     config("SHIP_SERVICE_URL",          default="http://ship-service:8000"),
    "reviews":       config("COMMENT_RATE_SERVICE_URL", default="http://comment-rate-service:8000"),
    "recommendations": config("RECOMMENDER_SERVICE_URL", default="http://recommender-ai-service:8000"),
    "staff":         config("STAFF_SERVICE_URL",         default="http://staff-service:8000"),
    "managers":      config("MANAGER_SERVICE_URL",       default="http://manager-service:8000"),
    "rag":           config("RAG_SERVICE_URL",           default="http://rag-service:8000"),
}

# Passthrough headers (exclude hop-by-hop)
PROXY_HEADERS_PASSTHROUGH = frozenset([
    "authorization",
    "content-type",
    "accept",
    "accept-language",
    "x-request-id",
])
