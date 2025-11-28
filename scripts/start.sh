#!/bin/bash
set -e

echo "Stopping containers..."
docker compose down

echo "Building images..."
docker compose build --no-cache

echo "Starting TimescaleDB..."
docker compose up -d timescaledb

echo ""
echo "Waiting for database to be ready..."
sleep 5

echo ""
echo "Running database migrations..."
docker compose run --rm api alembic upgrade head

echo ""
echo "Starting all services..."
docker compose up -d

echo ""
echo "Application started with fresh database!"
echo "To follow logs, run: docker compose logs -f"
