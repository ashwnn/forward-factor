#!/bin/bash

# Script to reset the database
# This will DELETE all existing data!

echo "⚠️  WARNING: This will DELETE all database data!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

echo "Stopping containers..."
docker compose down

echo "Removing SQLite database file..."
rm -f ./data/ffbot.db

echo "Removing old redis volume..."
rm -rf ./data/redis

echo "Building docker images..."
docker compose build --no-cache


echo "Starting containers..."
docker compose up -d redis

echo "Waiting for services to be ready..."
sleep 5

echo "Running database migrations..."
docker compose run --rm migrate

echo "Starting all services..."
docker compose up -d

echo ""
echo "✓ Database reset complete!"
echo "You can now register a new user."
