#!/bin/sh

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.2
done
echo "PostgreSQL is ready."

echo "Waiting for users table..."
while ! python - <<'PY'
import os
import psycopg2

try:
    conn = psycopg2.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.users')")
        raise SystemExit(0 if cursor.fetchone()[0] else 1)
except Exception:
    raise SystemExit(1)
PY
do
  sleep 0.2
done
echo "Users table is ready."

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
