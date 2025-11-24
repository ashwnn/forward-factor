#!/bin/bash
set -e

echo "Waiting for database to be ready..."

# Wait for PostgreSQL to be ready using pg_isready
# -h postgres: connect to host 'postgres' (service name in docker-compose)
# -U ffbot: connect as user 'ffbot'
until pg_isready -h postgres -U ffbot; do
  echo "Waiting for database..."
  sleep 2
done

echo "Database is ready! Running migrations..."
alembic upgrade head

echo "Migrations completed successfully!"
