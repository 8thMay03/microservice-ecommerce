from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Rating(models.Model):
    product_id = models.IntegerField(help_text="FK to product-service Product")
    customer_id = models.IntegerField(help_text="FK to customer-service Customer")
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (worst) to 5 (best)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ratings"
        unique_together = ("product_id", "customer_id")

    def __str__(self):
        return f"Rating(product={self.product_id}, customer={self.customer_id}, score={self.score})"


class Comment(models.Model):
    product_id = models.IntegerField(help_text="FK to product-service Product")
    customer_id = models.IntegerField(help_text="FK to customer-service Customer")
    customer_name = models.CharField(max_length=200, blank=True, default="")
    content = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment(product={self.product_id}, customer={self.customer_id})"
