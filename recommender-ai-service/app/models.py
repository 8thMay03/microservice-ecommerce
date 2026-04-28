"""
SQLAlchemy ORM models.
"""
import enum

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, UniqueConstraint, func

from app.database import Base


class UserAction(str, enum.Enum):
    """All trackable user behaviour actions."""

    view_product = "view_product"
    view_category = "view_category"
    search = "search"
    click_product = "click_product"
    add_to_wishlist = "add_to_wishlist"
    review_product = "review_product"
    purchase = "purchase"
    cancel_order = "cancel_order"
    add_to_cart = "add_to_cart"
    remove_from_cart = "remove_from_cart"


class RecommendationCache(Base):
    """Persisted recommendation results so we avoid re-computing on every request."""

    __tablename__ = "recommendation_cache"
    __table_args__ = (
        UniqueConstraint("customer_id", "product_id", name="uq_rec_cache_customer_product"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, doc="Higher is more relevant")
    strategy = Column(String(50), nullable=False, default="collaborative")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserBehavior(Base):
    """
    Raw user interaction events for behavioural analysis and model training.

    Columns
    -------
    id          — surrogate primary key
    user_id     — customer / user identifier (FK lives in customer-service)
    action      — enum: one of the UserAction values
    product_id  — nullable; relevant for product-level actions
    timestamp   — UTC time the event occurred (defaults to DB server time)
    metadata    — optional JSON string for extra context
                  (e.g. search query, category_id, session_id)
    """

    __tablename__ = "user_behavior"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    action = Column(
        Enum(UserAction, name="useraction", create_type=True),
        nullable=False,
        index=True,
    )
    product_id = Column(Integer, nullable=True, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    metadata = Column(String(500), nullable=True)
