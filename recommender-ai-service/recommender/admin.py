from django.contrib import admin
from .models import BehaviorEvent, RecommendationCache


@admin.register(BehaviorEvent)
class BehaviorEventAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_id", "event_type", "product_id", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["customer_id"]


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_id", "product_id", "score", "strategy", "created_at"]
    list_filter = ["strategy"]
