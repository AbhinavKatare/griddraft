# ==============================================================================
# Power Forecast Platform - Monorepo Makefile
# Provides standardized commands for local development, testing, and operations
# ==============================================================================

.PHONY: help setup dev dev-backend dev-frontend test test-backend test-frontend lint lint-backend lint-frontend ingest docker-up docker-down clean

PYTHON ?= python
NPM ?= npm

help:
	@echo "Available Make targets:"
	@echo "  make setup          - Install dependencies for backend and frontend"
	@echo "  make dev            - Instructions to run both dev servers"
	@echo "  make dev-backend    - Start FastAPI backend (http://127.0.0.1:8000)"
	@echo "  make dev-frontend   - Start Vite frontend dev server (http://127.0.0.1:5173)"
	@echo "  make test           - Run full test suite (pytest + frontend tsc)"
	@echo "  make test-backend   - Run backend pytest unit and edge-case tests"
	@echo "  make test-frontend  - Run frontend TypeScript typecheck and build"
	@echo "  make lint           - Run linting (ruff, mypy, and frontend checks)"
	@echo "  make ingest         - Fetch January 2026 data from Elexon BMRS into Parquet cache"
	@echo "  make docker-up      - Build and run services in Docker containers"
	@echo "  make docker-down    - Stop Docker containers"
	@echo "  make clean          - Remove temporary build files and python caches"

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
setup:
	@echo "--> Installing backend dependencies..."
	$(PYTHON) -m pip install -r backend/requirements.txt
	@echo "--> Installing frontend dependencies..."
	cd frontend && $(NPM) install
	@echo "--> Installing pre-commit hooks (if pre-commit available)..."
	-pre-commit install
	@echo "Setup completed successfully."

# ------------------------------------------------------------------------------
# Development
# ------------------------------------------------------------------------------
dev:
	@echo "To start development, open two terminal windows or background processes:"
	@echo "  Terminal 1: make dev-backend"
	@echo "  Terminal 2: make dev-frontend"

dev-backend:
	cd backend && $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	cd frontend && $(NPM) run dev -- --host 127.0.0.1 --port 5173

# ------------------------------------------------------------------------------
# Testing
# ------------------------------------------------------------------------------
test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest backend/tests -v

test-frontend:
	cd frontend && $(NPM) run build

# Run the canonical number verification script against the real Parquet cache.
# Exits non-zero if any figure drifts beyond tolerance.
verify-numbers:
	$(PYTHON) scripts/verify_numbers.py

# Run only the backend contract test that pins all canonical KPI values.
contract-test:
	$(PYTHON) -m pytest backend/tests/test_contract.py -v

# ------------------------------------------------------------------------------
# Linting & Formatting
# ------------------------------------------------------------------------------
lint: lint-backend lint-frontend

lint-backend:
	-$(PYTHON) -m ruff check backend/app
	-$(PYTHON) -m mypy backend/app --ignore-missing-imports

lint-frontend:
	cd frontend && $(NPM) run build

# ------------------------------------------------------------------------------
# Data Ingestion
# ------------------------------------------------------------------------------
ingest:
	@echo "--> Ingesting January 2026 FUELHH & WINDFOR from Elexon BMRS API..."
	cd backend && $(PYTHON) -m app.ingestion.run --start 2026-01-01 --end 2026-01-31

# ------------------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------------------
docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

# ------------------------------------------------------------------------------
# Clean
# ------------------------------------------------------------------------------
clean:
	@echo "--> Cleaning cache and build artifacts..."
	-rm -rf .pytest_cache frontend/dist backend/__pycache__
	-find . -type d -name "__pycache__" -exec rm -rf {} +
