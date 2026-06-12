from django.contrib import admin
from .models import StaffMember


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active"]
