import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_id", models.IntegerField(help_text="FK to order-service Order", unique=True)),
                ("customer_id", models.IntegerField(help_text="FK to customer-service Customer")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("COMPLETED", "Completed"),
                        ("FAILED", "Failed"), ("REFUNDED", "Refunded"),
                    ],
                    default="PENDING", max_length=20,
                )),
                ("method", models.CharField(
                    choices=[
                        ("CREDIT_CARD", "Credit Card"), ("DEBIT_CARD", "Debit Card"),
                        ("PAYPAL", "PayPal"), ("BANK_TRANSFER", "Bank Transfer"),
                    ],
                    default="CREDIT_CARD", max_length=20,
                )),
                ("transaction_id", models.UUIDField(default=uuid.uuid4, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "payments"},
        ),
    ]
