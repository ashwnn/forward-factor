#!/bin/bash
set -e

echo "==================================================================="
echo "Database Migration Script - Debug Mode"
echo "==================================================================="

echo ""
echo "Environment Variables:"
echo "-------------------------------------------------------------------"
echo "DATABASE_URL: ${DATABASE_URL}"
echo "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-<not set>}"
echo "DATABASE_PASSWORD: ${DATABASE_PASSWORD:-<not set>}"
echo ""

# Parse DATABASE_URL to show connection details (hide password)
if [[ $DATABASE_URL =~ postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
  echo "Parsed DATABASE_URL:"
  echo "  User: ${BASH_REMATCH[1]}"
  echo "  Password: ******* (hidden)"
  echo "  Host: ${BASH_REMATCH[3]}"
  echo "  Port: ${BASH_REMATCH[4]}"
  echo "  Database: ${BASH_REMATCH[5]}"
fi
echo ""

echo "Waiting for database to be ready..."
echo "-------------------------------------------------------------------"

# Wait for PostgreSQL to be ready using pg_isready
# -h postgres: connect to host 'postgres' (service name in docker-compose)
# -U ffbot: connect as user 'ffbot'
until pg_isready -h postgres -U ffbot; do
  echo "Waiting for database..."
  sleep 2
done

echo ""
echo "Database is ready! Testing connection..."
echo "-------------------------------------------------------------------"

# Test connection with psql to verify credentials
if PGPASSWORD="${POSTGRES_PASSWORD:-ffbot}" psql -h postgres -U ffbot -d ffbot -c "SELECT version();" > /dev/null 2>&1; then
  echo "✓ Database connection test successful"
else
  echo "✗ Database connection test FAILED"
  echo ""
  echo "Attempting to show PostgreSQL logs..."
  echo "Try running: docker logs ff-bot-postgres"
  exit 1
fi

echo ""
echo "Running Alembic migrations..."
echo "-------------------------------------------------------------------"
alembic upgrade head

echo ""
echo "==================================================================="
echo "Migrations completed successfully!"
echo "==================================================================="