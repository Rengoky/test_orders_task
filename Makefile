.PHONY: help install migrate up down logs test lint format clean seed

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

migrate: ## Run database migrations
	alembic upgrade head

migrate-down: ## Rollback last migration
	alembic downgrade -1

migrate-create: ## Create new migration (usage: make migrate-create name=description)
	alembic revision --autogenerate -m "$(name)"

up: ## Start services with docker-compose
	docker-compose up -d

down: ## Stop services
	docker-compose down

logs: ## View application logs
	docker-compose logs -f app

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=app --cov-report=html --cov-report=term

lint: ## Run linter
	ruff check app/ tests/

format: ## Format code
	black app/ tests/

typecheck: ## Run type checker
	mypy app/

qa: format lint typecheck ## Run all quality checks

clean: ## Clean cache and build files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage

seed: ## Seed database with sample data
	python scripts/seed_data.py

dev: ## Start development server locally
	uvicorn app.main:app --reload --log-level info

docker-build: ## Build docker image
	docker-compose build

docker-restart: ## Restart application container
	docker-compose restart app

psql: ## Connect to PostgreSQL
	docker-compose exec postgres psql -U user orders_db

redis-cli: ## Connect to Redis
	docker-compose exec redis redis-cli



