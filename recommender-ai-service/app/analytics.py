"""
Analytics module — ported from Django to SQLAlchemy async + httpx.
"""
import logging
from collections import defaultdict
from typing import Dict, List

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config as settings
from app.models import RecommendationCache

logger = logging.getLogger(__name__)


def _fetch_all_orders() -> List[dict]:
    """Lightweight fetch of all completed orders for analytics."""
    try:
        resp = httpx.get(
            f"{settings.ORDER_SERVICE_URL}/api/orders/",
            timeout=10.0,
        )
        resp.raise_for_status()
        orders = resp.json()
        completed = {"PAID", "SHIPPED", "DELIVERED"}
        return [o for o in orders if o.get("status") in completed]
    except httpx.RequestError as exc:
        logger.error("analytics: failed to fetch orders: %s", exc)
        return []


def _fetch_product_categories(product_ids: List[int]) -> Dict[int, int]:
    if not product_ids:
        return {}
    try:
        resp = httpx.post(
            f"{settings.PRODUCT_SERVICE_URL}/internal/products/bulk/",
            json={"ids": product_ids},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {p["id"]: p.get("category_id") for p in data}
    except httpx.RequestError as exc:
        logger.error("analytics: failed to fetch product categories: %s", exc)
        return {}


async def build_overview(db: AsyncSession) -> dict:
    """
    Compute:
      - category_purchase_counts: how many items sold per category
      - overall orders/items
      - simple recommendation conversion rate
    """
    orders = _fetch_all_orders()
    if not orders:
        return {
            "total_orders": 0,
            "total_items": 0,
            "category_purchase_counts": {},
            "recommendation_impressions": 0,
            "recommendation_conversions": 0,
            "recommendation_conversion_rate": 0.0,
        }

    total_items = 0
    all_product_ids: List[int] = []
    for o in orders:
        for it in o.get("items", []):
            total_items += it.get("quantity", 1)
            all_product_ids.append(it["product_id"])

    cat_map = _fetch_product_categories(list(set(all_product_ids)))
    cat_counts: Dict[int, int] = defaultdict(int)
    for o in orders:
        for it in o.get("items", []):
            pid = it["product_id"]
            qty = it.get("quantity", 1)
            cat_id = cat_map.get(pid)
            if cat_id is not None:
                cat_counts[cat_id] += qty

    # Recommendation conversion (approximate)
    impressions_result = await db.execute(select(func.count()).select_from(RecommendationCache))
    impressions: int = impressions_result.scalar_one()

    conversions = 0
    if impressions:
        purchased_pairs = set()
        for o in orders:
            cid = o.get("customer_id")
            for it in o.get("items", []):
                purchased_pairs.add((cid, it["product_id"]))

        rows_result = await db.execute(
            select(RecommendationCache.customer_id, RecommendationCache.product_id)
        )
        for customer_id, product_id in rows_result.all():
            if (customer_id, product_id) in purchased_pairs:
                conversions += 1

    rate = (conversions / impressions) if impressions else 0.0

    return {
        "total_orders": len(orders),
        "total_items": total_items,
        "category_purchase_counts": dict(cat_counts),
        "recommendation_impressions": impressions,
        "recommendation_conversions": conversions,
        "recommendation_conversion_rate": round(rate, 4),
    }
