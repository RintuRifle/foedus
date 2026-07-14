#!/bin/bash
# Foedus All-in-One Startup Script for Render Free Tier

echo "Starting Celery Worker..."
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 &

echo "Starting Scraper Scheduler Daemon..."
python -m scraper.scheduler &

echo "Starting FastAPI Server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
