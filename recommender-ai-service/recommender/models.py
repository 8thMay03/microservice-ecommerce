from django.db import models


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
