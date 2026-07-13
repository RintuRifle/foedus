# Foedus Backend — FastAPI + Celery worker + scraper (same image)
# Build context = repo ROOT (so the scraper package ships too):
#   docker build -f backend/Dockerfile -t foedus-backend .
FROM python:3.12-slim

# WeasyPrint system deps (PDF export) + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer-cached dependency install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code + scraper package
COPY backend/ ./
COPY scraper/ ./scraper/

# Non-root user
RUN useradd -m foedus && chown -R foedus:foedus /app
USER foedus

EXPOSE 8000

# Web (default). Other roles override the command:
#   worker:  celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
#   scraper: python -m scraper.scheduler --once
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
