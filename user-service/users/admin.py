from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
