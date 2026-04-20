from django.db import models


class CustomerBehaviorEvent(models.Model):
    """Append-only storefront signals for behavior-aware training (view / click / add_to_cart)."""

    class EventType(models.TextChoices):
        VIEW = "view", "View"
        CLICK = "click", "Click"
        ADD_TO_CART = "add_to_cart", "Add to cart"

    customer_id = models.IntegerField(db_index=True)
    product_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customer_behavior_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_id", "product_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} c={self.customer_id} p={self.product_id}"


class RecommendationCache(models.Model):
    """Persisted recommendation results so we avoid re-computing on every request."""
    customer_id = models.IntegerField(db_index=True)
    product_id = models.IntegerField()
    score = models.FloatField(help_text="Higher is more relevant")
    strategy = models.CharField(max_length=50, default="collaborative")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendation_cache"
        ordering = ["-score"]
        unique_together = ("customer_id", "product_id")
