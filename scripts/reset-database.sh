#!/bin/bash

# Script to reset the database when password changes
# This will DELETE all existing data!

echo "⚠️  WARNING: This will DELETE all database data!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

echo "Stopping containers..."
docker compose down

echo "Removing old database volume..."
rm -rf ./data/postgres

echo "Removing old redis volume..."
rm -rf ./data/redis

echo "Building docker images..."
docker compose build --no-cache


echo "Starting containers with new configuration..."
docker compose up -d postgres redis

echo "Waiting for database to be ready..."
sleep 10

echo "Running database migrations..."
docker compose exec api python -c "
import asyncio
from app.core.database import init_db

async def main():
    await init_db()
    print('✓ Database initialized')

asyncio.run(main())
"

echo "Starting all services..."
docker compose up -d

echo ""
echo "✓ Database reset complete!"
echo "You can now register a new user."
