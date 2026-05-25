"""
Pydantic schemas for request/response validation.
"""
from typing import List, Optional

from pydantic import BaseModel


# ── Shared ───────────────────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    product_id: int
    score: float
    title: str
    brand: str
    price: Optional[float]
    cover_image: str
    category_id: Optional[int]
    product_type: str


# ── User-based recommendations ────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    customer_id: int
    strategy: str
    recommendations: List[RecommendationItem]


# ── Item-based recommendations ────────────────────────────────────────────────

class ItemRecommendationResponse(BaseModel):
    product_id: int
    recommendations: List[RecommendationItem]


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsOverviewResponse(BaseModel):
    total_orders: int
    total_items: int
    category_purchase_counts: dict
    recommendation_impressions: int
    recommendation_conversions: int
    recommendation_conversion_rate: float


# ── User Behavior ─────────────────────────────────────────────────────────────

class BehaviorEventRequest(BaseModel):
    """Payload to record a single user interaction."""

    user_id: int
    action: str          # validated against UserAction enum in the route
    product_id: Optional[int] = None
    timestamp: Optional[str] = None   # ISO-8601; if omitted, DB server time is used
    metadata: Optional[str] = None    # free-form JSON string (query text, session_id, …)


class BehaviorEventResponse(BaseModel):
    id: int
    user_id: int
    action: str
    product_id: Optional[int]
    timestamp: str
    metadata: Optional[str]


class BehaviorListResponse(BaseModel):
    total: int
    events: List[BehaviorEventResponse]
