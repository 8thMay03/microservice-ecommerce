"""
FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.routes.behavior import router as behavior_router
from app.routes.recommendations import router as recommendations_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="Recommender AI Service",
    description="Product recommendation engine using collaborative filtering and behavior tracking.",
    version="2.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Database init ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "ALTER TABLE recommendation_cache "
                "ALTER COLUMN created_at SET DEFAULT now()"
            )
        )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(
    recommendations_router,
    prefix="/api/recommendations",
    tags=["recommendations"],
)
app.include_router(
    behavior_router,
    prefix="/api/behavior",
    tags=["behavior"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
