from django.contrib import admin
from .models import CustomerBehaviorEvent, RecommendationCache


@admin.register(CustomerBehaviorEvent)
class CustomerBehaviorEventAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_id", "product_id", "event_type", "created_at"]
    list_filter = ["event_type"]


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_id", "product_id", "score", "strategy", "created_at"]
    list_filter = ["strategy"]
