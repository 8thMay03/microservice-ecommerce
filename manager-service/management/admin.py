from django.contrib import admin
from .models import ManagerUser


@admin.register(ManagerUser)
class ManagerUserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "first_name", "last_name", "created_at"]
