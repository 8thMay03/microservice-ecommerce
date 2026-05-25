"""
Recommendation API routes.

GET /api/recommendations/{customer_id}
GET /api/recommendations/item/{product_id}
GET /api/recommendations/analytics/overview
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config as settings
from app.analytics import build_overview
from app.database import get_db
from app.engine import get_recommendations, item_based_similar
from app.models import RecommendationCache
from app.schemas import (
    AnalyticsOverviewResponse,
    ItemRecommendationResponse,
    RecommendationItem,
    RecommendationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fetch_product_details(product_ids: list[int]) -> dict:
    if not product_ids:
        return {}
    try:
        resp = httpx.post(
            f"{settings.PRODUCT_SERVICE_URL}/internal/products/bulk/",
            json={"ids": product_ids},
            timeout=5.0,
        )
        resp.raise_for_status()
        return {p["id"]: p for p in resp.json()}
    except httpx.RequestError as exc:
        logger.warning("Could not fetch product details: %s", exc)
        return {}


def _build_rows(pairs: list[tuple[int, float]], product_details: dict) -> list[RecommendationItem]:
    rows = []
    for product_id, score in pairs:
        if product_id not in product_details:
            continue
        detail = product_details[product_id]
        rows.append(
            RecommendationItem(
                product_id=product_id,
                score=round(score, 4),
                title=detail.get("title", ""),
                brand=detail.get("brand", ""),
                price=detail.get("price"),
                cover_image=detail.get("cover_image", ""),
                category_id=detail.get("category_id"),
                product_type=detail.get("product_type", ""),
            )
        )
    return rows


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/{customer_id}",
    response_model=RecommendationResponse,
    summary="Get recommendations for a customer",
)
async def get_customer_recommendations(
    customer_id: int,
    limit: int = Query(10, ge=1, le=100),
    refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a ranked list of recommended products for a customer.
    Uses behavior_dl (Neural CF) when a trained checkpoint exists; otherwise
    collaborative filtering; then popularity for cold users.
    """
    if not refresh:
        cached_result = await db.execute(
            select(RecommendationCache.product_id, RecommendationCache.score)
            .where(RecommendationCache.customer_id == customer_id)
            .order_by(RecommendationCache.score.desc())
            .limit(limit)
        )
        cached = cached_result.all()
        if cached:
            pairs = [(row.product_id, row.score) for row in cached]
            product_details = _fetch_product_details([pid for pid, _ in pairs])
            results = _build_rows(pairs, product_details)
            if results:
                return RecommendationResponse(
                    customer_id=customer_id,
                    strategy="cached",
                    recommendations=results,
                )

    # Compute fresh recommendations
    recs, strategy = get_recommendations(customer_id, limit)

    product_details = _fetch_product_details([pid for pid, _ in recs])
    recs = [(pid, s) for pid, s in recs if pid in product_details]

    # Persist only rows that still exist in product-service
    await db.execute(
        delete(RecommendationCache).where(RecommendationCache.customer_id == customer_id)
    )
    if recs:
        db.add_all(
            [
                RecommendationCache(
                    customer_id=customer_id,
                    product_id=product_id,
                    score=score,
                    strategy=strategy,
                )
                for product_id, score in recs
            ]
        )
        await db.commit()

    results = _build_rows(recs, product_details)
    return RecommendationResponse(
        customer_id=customer_id,
        strategy=strategy,
        recommendations=results,
    )


@router.get(
    "/item/{product_id}",
    response_model=ItemRecommendationResponse,
    summary="Get item-based similar products",
)
async def get_item_recommendations(
    product_id: int,
    limit: int = Query(8, ge=1, le=100),
):
    """
    'Because you viewed X, you might like Y' style suggestions.
    """
    recs = item_based_similar(product_id, limit)
    product_details = _fetch_product_details([pid for pid, _ in recs])
    recs = [(pid, s) for pid, s in recs if pid in product_details]
    results = _build_rows(recs, product_details)
    return ItemRecommendationResponse(product_id=product_id, recommendations=results)


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Analytics overview for admin/marketing dashboards",
)
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Lightweight analytics: order totals, category counts, recommendation conversion rate."""
    data = await build_overview(db)
    return AnalyticsOverviewResponse(**data)
