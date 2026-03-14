from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_id", models.IntegerField(help_text="FK to customer-service Customer")),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("PAID", "Paid"),
                        ("SHIPPED", "Shipped"), ("DELIVERED", "Delivered"),
                        ("CANCELLED", "Cancelled"), ("REFUNDED", "Refunded"),
                    ],
                    default="PENDING", max_length=20,
                )),
                ("total_amount", models.DecimalField(
                    decimal_places=2, max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                )),
                ("shipping_address", models.TextField()),
                ("payment_method", models.CharField(default="CREDIT_CARD", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "orders", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("book_id", models.IntegerField(help_text="FK to book-service Book")),
                ("book_title", models.CharField(max_length=300)),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="orders.order",
                )),
            ],
            options={"db_table": "order_items"},
        ),
    ]
