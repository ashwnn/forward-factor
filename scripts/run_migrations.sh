#!/bin/bash
set -e

echo "==================================================================="
echo "Database Migration Script"
echo "==================================================================="

echo ""
echo "Environment Variables:"
echo "-------------------------------------------------------------------"
echo "DATABASE_URL: ${DATABASE_URL}"
echo ""

echo "Running Alembic migrations..."
echo "-------------------------------------------------------------------"
alembic upgrade head

echo ""
echo "==================================================================="
echo "Migrations completed successfully!"
echo "==================================================================="