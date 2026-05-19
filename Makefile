.PHONY: help install dev lint test format build clean docker

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	pip install -e .

dev: ## Install with all dev dependencies
	pip install -e ".[all]"
	pre-commit install

lint: ## Run linters
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff format src/ tests/
	ruff check --fix src/ tests/

test: ## Run tests with coverage
	pytest --tb=short --cov=testloom --cov-report=term-missing

test-fast: ## Run tests without coverage
	pytest --tb=short -q

build: ## Build distribution packages
	python -m build

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

docker: ## Build Docker image
	docker build -f docker/Dockerfile -t testloom:latest .

docker-up: ## Start dev environment with Docker Compose
	docker compose -f docker/docker-compose.yml up -d

docker-down: ## Stop dev environment
	docker compose -f docker/docker-compose.yml down
