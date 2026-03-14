from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("book_id", models.IntegerField(help_text="FK to book-service Book")),
                ("customer_id", models.IntegerField(help_text="FK to customer-service Customer")),
                ("score", models.PositiveSmallIntegerField(
                    help_text="Rating from 1 (worst) to 5 (best)",
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5),
                    ],
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ratings",
                "unique_together": {("book_id", "customer_id")},
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("book_id", models.IntegerField(help_text="FK to book-service Book")),
                ("customer_id", models.IntegerField(help_text="FK to customer-service Customer")),
                ("content", models.TextField()),
                ("is_approved", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "comments",
                "ordering": ["-created_at"],
            },
        ),
    ]
