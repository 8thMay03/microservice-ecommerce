from django.db import models


class BehaviorEvent(models.Model):
    """
    Fine-grained customer actions (views, clicks, cart, purchases).
    Used to build temporal sequences for RNN/LSTM/BiLSTM next-event training.
    """

    EVENT_VIEW = "view"
    EVENT_CLICK = "click"
    EVENT_ADD_TO_CART = "add_to_cart"
    EVENT_PURCHASE = "purchase"

    customer_id = models.IntegerField(db_index=True)
    product_id = models.IntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=32, db_index=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "behavior_events"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["customer_id", "created_at"],
                name="behav_ev_cust_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"BehaviorEvent(c={self.customer_id}, {self.event_type})"


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
