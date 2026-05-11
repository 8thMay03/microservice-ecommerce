"""
Migrate data from legacy customer_db, staff_db, manager_db into unified user_db.

Usage (inside user-service container):
  python manage.py migrate_legacy_data

This command connects to the old databases via psycopg2, reads all users,
and creates them in the unified users table preserving original IDs and password hashes.
"""
import psycopg2
from django.core.management.base import BaseCommand
from django.db import connection
from users.models import User


class Command(BaseCommand):
    help = "Migrate data from legacy customer/staff/manager databases into unified user_db"

    def add_arguments(self, parser):
        parser.add_argument("--customer-db-host", default="customer-db")
        parser.add_argument("--customer-db-name", default="customer_db")
        parser.add_argument("--customer-db-user", default="postgres")
        parser.add_argument("--customer-db-password", default="postgres123")
        parser.add_argument("--staff-db-host", default="staff-db")
        parser.add_argument("--staff-db-name", default="staff_db")
        parser.add_argument("--staff-db-user", default="postgres")
        parser.add_argument("--staff-db-password", default="postgres123")
        parser.add_argument("--manager-db-host", default="manager-db")
        parser.add_argument("--manager-db-name", default="manager_db")
        parser.add_argument("--manager-db-user", default="postgres")
        parser.add_argument("--manager-db-password", default="postgres123")

    def handle(self, *args, **options):
        self._migrate_customers(options)
        self._migrate_staff(options)
        self._migrate_managers(options)
        self._reset_sequence()

    def _migrate_customers(self, options):
        try:
            conn = psycopg2.connect(
                host=options["customer_db_host"],
                dbname=options["customer_db_name"],
                user=options["customer_db_user"],
                password=options["customer_db_password"],
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not connect to customer_db: {e}"))
            return

        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, password, first_name, last_name, phone, address, "
            "is_active, last_login, created_at, updated_at FROM customers"
        )
        count = 0
        for row in cur.fetchall():
            user, created = User.objects.get_or_create(
                email=row[1],
                defaults={
                    "first_name": row[3] or "",
                    "last_name": row[4] or "",
                    "phone": row[5] or "",
                    "address": row[6] or "",
                    "is_active": row[7],
                    "role": "CUSTOMER",
                    "created_at": row[9],
                    "updated_at": row[10],
                },
            )
            if created:
                user.password = row[2]
                user.last_login = row[8]
                user.save(update_fields=["password", "last_login"])
                User.objects.filter(pk=user.pk).update(id=row[0])
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Migrated {count} customers"))
        cur.close()
        conn.close()

    def _migrate_staff(self, options):
        try:
            conn = psycopg2.connect(
                host=options["staff_db_host"],
                dbname=options["staff_db_name"],
                user=options["staff_db_user"],
                password=options["staff_db_password"],
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not connect to staff_db: {e}"))
            return

        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, password, first_name, last_name, role, "
            "is_active, is_admin, last_login, created_at, updated_at FROM staff_members"
        )
        count = 0
        for row in cur.fetchall():
            user, created = User.objects.get_or_create(
                email=row[1],
                defaults={
                    "first_name": row[3] or "",
                    "last_name": row[4] or "",
                    "is_active": row[6],
                    "role": "STAFF",
                    "staff_role": row[5] or "",
                    "is_admin": row[7],
                    "is_staff_flag": True,
                    "created_at": row[9],
                    "updated_at": row[10],
                },
            )
            if created:
                user.password = row[2]
                user.last_login = row[8]
                user.save(update_fields=["password", "last_login"])
                User.objects.filter(pk=user.pk).update(id=row[0])
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Migrated {count} staff members"))
        cur.close()
        conn.close()

    def _migrate_managers(self, options):
        try:
            conn = psycopg2.connect(
                host=options["manager_db_host"],
                dbname=options["manager_db_name"],
                user=options["manager_db_user"],
                password=options["manager_db_password"],
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not connect to manager_db: {e}"))
            return

        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, password, first_name, last_name, "
            "is_active, last_login, created_at FROM managers"
        )
        count = 0
        for row in cur.fetchall():
            user, created = User.objects.get_or_create(
                email=row[1],
                defaults={
                    "first_name": row[3] or "",
                    "last_name": row[4] or "",
                    "is_active": row[5],
                    "role": "MANAGER",
                    "is_admin": True,
                    "is_staff_flag": True,
                    "created_at": row[7],
                },
            )
            if created:
                user.password = row[2]
                user.last_login = row[6]
                user.save(update_fields=["password", "last_login"])
                User.objects.filter(pk=user.pk).update(id=row[0])
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Migrated {count} managers"))
        cur.close()
        conn.close()

    def _reset_sequence(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users))")
        self.stdout.write(self.style.SUCCESS("Reset users_id_seq to MAX(id)"))
