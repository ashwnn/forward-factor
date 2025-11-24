#!/bin/bash
set -e

echo "Waiting for database to be ready..."

# Wait for PostgreSQL to be ready
max_retries=30
counter=0

while [ $counter -lt $max_retries ]; do
    if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def check_db():
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute('SELECT 1')
        await engine.dispose()
        return True
    except Exception as e:
        print(f'Database not ready: {e}')
        return False

exit(0 if asyncio.run(check_db()) else 1)
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    
    counter=$((counter + 1))
    echo "Waiting for database... ($counter/$max_retries)"
    sleep 2
done

if [ $counter -eq $max_retries ]; then
    echo "ERROR: Database did not become ready in time"
    exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"
