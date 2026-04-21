.DEFAULT_GOAL := help
PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help venv install dev test lint format build clean docker

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)

install: venv ## Install dependencies
	$(BIN)/pip install -e ".[dev]"

dev: install ## Install deps and start (backend + frontend build)
	@test -f .env || cp .env.example .env
	./start.sh

dev-api: install ## Run backend API server only (hot reload)
	@test -f .env || cp .env.example .env
	$(BIN)/uvicorn uso.api.app:create_app --factory --reload --port 8000

dev-ui: ## Run SvelteKit dev server
	cd frontend && npm run dev

dev-full: install ## Run backend and frontend dev servers concurrently
	./start.sh --dev

test: ## Run tests
	$(BIN)/python -m pytest tests/ -q --tb=short

lint: ## Run linter
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format: ## Auto-format code
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

build: ## Build wheel + sdist
	$(BIN)/python -m build

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache

docker: ## Build Docker image
	docker build -t uso:latest .
