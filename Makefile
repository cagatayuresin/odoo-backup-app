SHELL := /bin/bash
.PHONY: format lint type security deps deadcode complexity docker-check audit all help

BACKEND := backend
PYTHON  := python3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

format: ## Ruff format + auto-fix
	cd $(BACKEND) && ruff format app tests
	cd $(BACKEND) && ruff check --fix app tests

lint: ## Ruff lint check (no fix)
	cd $(BACKEND) && ruff check app tests

type: ## mypy strict type check
	cd $(BACKEND) && mypy --config-file pyproject.toml app

security: ## Bandit security scan
	cd $(BACKEND) && bandit -c pyproject.toml -r app

deps: ## Deptry + pip-audit dependency checks
	cd $(BACKEND) && deptry app
	cd $(BACKEND) && pip-audit -r requirements.in --skip-editable

deadcode: ## Vulture dead-code detection + ruff F401/F841/ERA
	cd $(BACKEND) && vulture app
	cd $(BACKEND) && ruff check --select F401,F841,ERA app

complexity: ## Ruff complexity rules
	cd $(BACKEND) && ruff check --select C90,PL app

docker-check: ## Hadolint + Trivy image/config scan
	hadolint backend/Dockerfile
	trivy config backend/Dockerfile
	@echo "Run 'trivy image odoo-backup-app:latest' after building to scan the image."

audit: lint type security deps deadcode complexity ## Run all checks sequentially

all: format audit docker-check ## Format + full audit + docker-check

test: ## Run pytest
	cd $(BACKEND) && pytest

test-cov: ## Run pytest with coverage HTML report
	cd $(BACKEND) && pytest --cov-report=html

frontend-build: ## Build the frontend
	cd frontend && npm ci && npm run build

frontend-dev: ## Start Vite dev server
	cd frontend && npm run dev

dev-up: ## Start dev compose stack
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

prod-up: ## Start production compose stack
	docker compose up -d --build
