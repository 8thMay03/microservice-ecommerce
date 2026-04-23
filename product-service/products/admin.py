from django.contrib import admin
from .models import Product, ProductInventory


class ProductInventoryInline(admin.StackedInline):
    model = ProductInventory
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "product_type", "sku", "price", "is_active", "created_at")
    list_filter = ("product_type", "is_active")
    search_fields = ("title", "brand", "sku")
    inlines = [ProductInventoryInline]
