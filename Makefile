
# Foedus — Development Commands

.PHONY: help dev stop migrate test scrape lint clean

help: ## Show this help message
	@echo "Foedus Development Commands:"
	@echo "────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

infra-up: ## Start Docker services (postgres, redis, qdrant)
	docker-compose up -d
	@echo "✅ Services started: PostgreSQL :5432 | Redis :6379 | Qdrant :6333"

infra-down: ## Stop Docker services
	docker-compose down

infra-reset: ## Stop services and DELETE all data volumes
	docker-compose down -v
	@echo "🗑️  All data volumes removed"

install: ## Install Python dependencies
	cd backend && pip install -r requirements.txt

dev: ## Run FastAPI dev server with hot-reload
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run Alembic migrations (upgrade to head)
	cd backend && alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="add xyz table")
	cd backend && alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

scrape: ## Run scraper once (fetch + process + store)
	cd backend && python -m scraper.scheduler --once

scrape-daemon: ## Run scraper as scheduled daemon
	cd backend && python -m scraper.scheduler

worker: ## Start Celery worker
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

flower: ## Start Flower (Celery monitoring UI)
	cd backend && celery -A app.tasks.celery_app flower --port=5555

test: ## Run all tests
	cd backend && pytest -v --tb=short

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit -v --tb=short

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration -v --tb=short

lint: ## Run linters (black + flake8 + isort)
	cd backend && black . && isort . && flake8 .

format: ## Auto-format code
	cd backend && black . && isort .

clean: ## Remove Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete 2>/dev/null; \
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; \
	echo "🧹 Cleaned up cache files"

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Run Next.js dev server
	cd frontend && npm run dev
