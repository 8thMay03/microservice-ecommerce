# Generated manually for sequence behavior models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recommender", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BehaviorEvent",
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
                (
                    "product_id",
                    models.IntegerField(blank=True, null=True),
                ),
                ("event_type", models.CharField(db_index=True, max_length=32)),
                ("created_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "db_table": "behavior_events",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(
                        fields=["customer_id", "created_at"],
                        name="behav_ev_cust_created_idx",
                    ),
                ],
            },
        ),
    ]
