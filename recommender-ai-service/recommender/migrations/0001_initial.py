from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RecommendationCache",
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
                ("book_id", models.IntegerField()),
                (
                    "score",
                    models.FloatField(help_text="Higher is more relevant"),
                ),
                (
                    "strategy",
                    models.CharField(default="collaborative", max_length=50),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "recommendation_cache",
                "ordering": ["-score"],
                "unique_together": {("customer_id", "book_id")},
            },
        ),
    ]
