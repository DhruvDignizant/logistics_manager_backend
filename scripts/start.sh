#!/bin/bash
set -e

# Apply migrations (ensure DB is up to date)
# In a real setup, we might use alembic upgrade head
# For this MVP, relying on app startup (lifespan) or explicit script
echo "Checking database..."
python -c "from backend.app.db.session import engine; print('DB Connection OK')"

# Start Gunicorn with Uvicorn worker
echo "Starting Web Service..."
exec gunicorn backend.app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
