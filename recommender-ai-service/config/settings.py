from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-recommender-dev-key")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "recommender",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

DB_ENGINE = config("DB_ENGINE", default="postgres").lower()
if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="recommender_db"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres123"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

CORS_ALLOW_ALL_ORIGINS = True
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Inter-service URLs
ORDER_SERVICE_URL = config("ORDER_SERVICE_URL", default="http://order-service:8000")
PRODUCT_SERVICE_URL = config("PRODUCT_SERVICE_URL", default="http://product-service:8000")
COMMENT_RATE_SERVICE_URL = config(
    "COMMENT_RATE_SERVICE_URL", default="http://comment-rate-service:8000"
)

# Deep learning behavior model (Neural CF checkpoint)
BEHAVIOR_MODEL_PATH = config(
    "BEHAVIOR_MODEL_PATH",
    default=str(BASE_DIR / "recommender" / "weights" / "behavior_model.pt"),
)
BEHAVIOR_DL_ENABLED = config("BEHAVIOR_DL_ENABLED", default=True, cast=bool)
# cpu | cuda | cuda:0 | mps | auto (CUDA then MPS then CPU)
BEHAVIOR_TORCH_DEVICE = config("BEHAVIOR_TORCH_DEVICE", default="auto")

# Per-signal strength when merging into one user–item affinity (max wins). Purchase comes from orders.
BEHAVIOR_WEIGHT_PURCHASE = config("BEHAVIOR_WEIGHT_PURCHASE", default=1.0, cast=float)
BEHAVIOR_WEIGHT_ADD_TO_CART = config(
    "BEHAVIOR_WEIGHT_ADD_TO_CART", default=0.75, cast=float
)
BEHAVIOR_WEIGHT_CLICK = config("BEHAVIOR_WEIGHT_CLICK", default=0.4, cast=float)
BEHAVIOR_WEIGHT_VIEW = config("BEHAVIOR_WEIGHT_VIEW", default=0.15, cast=float)
