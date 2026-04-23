from django.contrib import admin
from .models import Rating, Comment


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["id", "product_id", "customer_id", "score", "created_at"]
    list_filter = ["score"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "product_id", "customer_id", "is_approved", "created_at"]
    list_filter = ["is_approved"]
    actions = ["approve_comments"]

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
