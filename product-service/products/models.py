from django.db import models
from django.core.validators import MinValueValidator


class Product(models.Model):
    class ProductType(models.TextChoices):
        BOOK = "BOOK", "Book"
        ELECTRONICS = "ELECTRONICS", "Electronics"
        CLOTHING = "CLOTHING", "Clothing"
        FOOD = "FOOD", "Food & Beverages"
        HOME = "HOME", "Home & Garden"
        SPORTS = "SPORTS", "Sports & Outdoors"

    title = models.CharField(max_length=300)
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.BOOK,
    )
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    cover_image = models.URLField(blank=True)
    category_id = models.IntegerField(help_text="FK to catalog-service Category")
    brand = models.CharField(max_length=200, blank=True, help_text="Brand or author")

    # Flexible attributes per product type
    # Books:       {"author": "...", "isbn": "...", "pages": 300, "language": "en", "published_date": "2024-01-01"}
    # Electronics: {"warranty": "12 months", "specs": {"ram": "8GB", "storage": "256GB"}}
    # Clothing:    {"sizes": ["S","M","L"], "color": "Red", "material": "Cotton"}
    # Food:        {"weight": "500g", "expiry": "2025-12-31", "ingredients": [...]}
    # Home:        {"dimensions": "50x30x20cm", "material": "Wood"}
    # Sports:      {"sport_type": "Running", "size": "42"}
    attributes = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_product_type_display()})"


class ProductInventory(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    warehouse_location = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_inventory"
        verbose_name_plural = "product inventories"

    def __str__(self):
        return f"Inventory for {self.product.title}: {self.stock_quantity}"
