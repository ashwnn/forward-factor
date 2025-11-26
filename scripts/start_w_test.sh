#!/bin/bash
set -e

echo "==================================================================="
echo "🧪 Forward Factor - Test & Start"
echo "==================================================================="

echo ""
echo "🔄 Building containers to ensure latest dependencies..."
docker compose build worker

echo ""
echo "🏃 Running tests..."
# Run pytest in the worker container. 
# We use 'run --rm' to spin up a temporary container.
# We override the command to run pytest.
if docker compose run --rm worker pytest tests/unit/services/test_signal_engine.py tests/unit/providers/test_provider_models.py -v; then
    echo ""
    echo "✅ Tests passed!"
    
    echo ""
    echo "🚀 Starting application..."
    ./scripts/start.sh
else
    echo ""
    echo "❌ Tests failed! Aborting start."
    exit 1
fi
