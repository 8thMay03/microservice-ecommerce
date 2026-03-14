import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.IntegerField(help_text="FK to order-service Order", unique=True)),
                ("customer_id", models.IntegerField(help_text="FK to customer-service Customer")),
                ("shipping_address", models.TextField()),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("PROCESSING", "Processing"),
                        ("SHIPPED", "Shipped"), ("IN_TRANSIT", "In Transit"),
                        ("DELIVERED", "Delivered"), ("RETURNED", "Returned"),
                    ],
                    default="PENDING", max_length=20,
                )),
                ("tracking_number", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("carrier", models.CharField(default="BookStore Logistics", max_length=100)),
                ("estimated_delivery", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "shipments"},
        ),
    ]
