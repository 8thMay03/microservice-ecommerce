# Generated manually for behavior event tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recommender", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerBehaviorEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("customer_id", models.IntegerField(db_index=True)),
                ("product_id", models.IntegerField(db_index=True)),
                (
                    "event_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("view", "View"),
                            ("click", "Click"),
                            ("add_to_cart", "Add to cart"),
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "customer_behavior_event",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["customer_id", "product_id"],
                        name="recommender_cust_prod_idx",
                    ),
                ],
            },
        ),
    ]
