#!/bin/sh

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.2
done
echo "PostgreSQL is ready."

exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --log-level info
