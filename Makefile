# OkChat — Developer Makefile
# Run `make help` to see all available commands

.PHONY: help install dev test lint typecheck migrate build up down clean

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	poetry install --with dev

dev:  ## Start local development server with hot reload
	docker compose up postgres redis -d
	poetry run uvicorn okchat.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

up:  ## Start all services via docker compose
	docker compose up --build -d

up-tools:  ## Start all services including pgAdmin and Redis Commander
	docker compose --profile tools up --build -d

down:  ## Stop all docker compose services
	docker compose down

test:  ## Run all tests
	poetry run pytest tests/ -v

test-unit:  ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration:  ## Run integration tests only
	poetry run pytest tests/integration/ -v

lint:  ## Run Ruff linter
	poetry run ruff check src/ tests/

lint-fix:  ## Run Ruff linter with auto-fix
	poetry run ruff check --fix src/ tests/

typecheck:  ## Run MyPy type checker
	poetry run mypy src/

format:  ## Format code with Ruff
	poetry run ruff format src/ tests/

migrate:  ## Run Alembic migrations
	poetry run alembic upgrade head

migrate-create:  ## Create a new migration (usage: make migrate-create MSG="add users table")
	poetry run alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:  ## Roll back last migration
	poetry run alembic downgrade -1

build:  ## Build production Docker image
	docker build -t okchat-api:latest .

clean:  ## Remove Python caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete; \
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov coverage.xml dist/
