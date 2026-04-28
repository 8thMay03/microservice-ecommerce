"""
Application settings loaded from environment variables / .env file.
Replaces Django's settings.py.
"""
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Database ────────────────────────────────────────────────────────────────
DB_ENGINE: str = config("DB_ENGINE", default="postgres").lower()

if DB_ENGINE == "sqlite":
    DATABASE_URL: str = config(
        "DATABASE_URL",
        default=f"sqlite+aiosqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
else:
    DB_NAME: str = config("DB_NAME", default="recommender_db")
    DB_USER: str = config("DB_USER", default="postgres")
    DB_PASSWORD: str = config("DB_PASSWORD", default="postgres123")
    DB_HOST: str = config("DB_HOST", default="localhost")
    DB_PORT: str = config("DB_PORT", default="5432")
    DATABASE_URL = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

# ── Inter-service URLs ───────────────────────────────────────────────────────
ORDER_SERVICE_URL: str = config(
    "ORDER_SERVICE_URL", default="http://order-service:8000"
)
PRODUCT_SERVICE_URL: str = config(
    "PRODUCT_SERVICE_URL", default="http://product-service:8000"
)
COMMENT_RATE_SERVICE_URL: str = config(
    "COMMENT_RATE_SERVICE_URL", default="http://comment-rate-service:8000"
)

# ── Deep-learning behavior model ─────────────────────────────────────────────
BEHAVIOR_MODEL_PATH: str = config(
    "BEHAVIOR_MODEL_PATH",
    default=str(BASE_DIR / "weights" / "behavior_model.pt"),
)
BEHAVIOR_DL_ENABLED: bool = config("BEHAVIOR_DL_ENABLED", default=True, cast=bool)
# cpu | cuda | cuda:0 | mps | auto (CUDA then MPS then CPU)
BEHAVIOR_TORCH_DEVICE: str = config("BEHAVIOR_TORCH_DEVICE", default="auto")

# ── Server ───────────────────────────────────────────────────────────────────
DEBUG: bool = config("DEBUG", default=True, cast=bool)
CORS_ALLOW_ALL_ORIGINS: bool = True
