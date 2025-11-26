#!/bin/bash
set -e

echo "==================================================================="
echo "🚀 Forward Factor - Start (Preserving Data)"
echo "==================================================================="

echo ""
echo "🛑 Stopping containers (if running)..."
docker compose down --remove-orphans

echo ""
echo "🏗️  Building and starting containers..."
docker compose up --build -d

echo ""
echo "==================================================================="
echo "✅ Application started!"
echo "==================================================================="
echo "To follow logs, run: docker compose logs -f"
