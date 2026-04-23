from django.contrib import admin
from .models import RecommendationCache


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_id", "product_id", "score", "strategy", "created_at"]
    list_filter = ["strategy"]
