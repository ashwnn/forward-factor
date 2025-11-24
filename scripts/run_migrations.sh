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
echo "Database is ready! Waiting for full initialization..."
# Give PostgreSQL a moment to fully initialize after accepting connections
sleep 3

echo "Testing database connection with credentials..."
echo "-------------------------------------------------------------------"

# Test connection with psql to verify credentials with retry logic
MAX_RETRIES=30
RETRY_COUNT=0
CONNECTION_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if PGPASSWORD="${POSTGRES_PASSWORD:-ffbot}" psql -h postgres -U ffbot -d ffbot -c "SELECT version();" > /dev/null 2>&1; then
    echo "✓ Database connection test successful (attempt $((RETRY_COUNT + 1)))"
    CONNECTION_SUCCESS=true
    break
  else
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "✗ Connection attempt $RETRY_COUNT failed, retrying in 2 seconds..."
      sleep 2
    fi
  fi
done

if [ "$CONNECTION_SUCCESS" = false ]; then
  echo ""
  echo "========================================="
  echo "✗ DATABASE CONNECTION FAILED"
  echo "========================================="
  echo ""
  echo "Failed to connect after $MAX_RETRIES attempts."
  echo ""
  echo "PostgreSQL logs (last 30 lines):"
  echo "-----------------------------------------"
  docker logs ff-bot-postgres --tail 30 2>&1 || echo "Could not retrieve PostgreSQL logs"
  echo ""
  echo "Troubleshooting steps:"
  echo "1. Verify POSTGRES_PASSWORD in .env matches the value in DATABASE_URL"
  echo "2. Check if PostgreSQL container started correctly: docker ps -a"
  echo "3. Try restarting with clean volumes: docker-compose down -v && docker-compose up -d"
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