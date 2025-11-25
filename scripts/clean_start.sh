#!/bin/bash
set -e

echo "==================================================================="
echo "🧹 Forward Factor - Deep Clean & Restart"
echo "==================================================================="

# 1. Stop all running containers
echo ""
echo "🛑 Stopping containers..."
docker compose down --remove-orphans

# 2. Clean Python Cache
echo ""
echo "🐍 Cleaning Python cache (__pycache__, .pyc)..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 3. Clean Frontend Cache
echo ""
echo "⚛️  Cleaning Frontend cache (.next)..."
if [ -d "frontend/.next" ]; then
    rm -rf frontend/.next
    echo "   - Removed frontend/.next"
fi

# 4. Rebuild Containers (No Cache)
echo ""
echo "🏗️  Rebuilding containers (forcing no-cache)..."
docker compose build --no-cache

# 5. Start Application
echo ""
echo "🚀 Starting application..."
docker compose up -d

echo ""
echo "==================================================================="
echo "✅ Clean start complete!"
echo "==================================================================="
echo "To follow logs, run: docker compose logs -f"
