from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("CUSTOMER", "Customer"),
                            ("STAFF", "Staff"),
                            ("MANAGER", "Manager"),
                        ],
                        default="CUSTOMER",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("phone", models.CharField(blank=True, default="", max_length=20)),
                ("address", models.TextField(blank=True, default="")),
                (
                    "staff_role",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("WAREHOUSE", "Warehouse Staff"),
                            ("SALES", "Sales Staff"),
                            ("SUPPORT", "Customer Support"),
                            ("MANAGER", "Manager"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("is_admin", models.BooleanField(default=False)),
                ("is_staff_flag", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "users",
            },
        ),
    ]
