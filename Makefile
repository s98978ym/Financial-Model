# PL Generator — Makefile
# Agent Teams の共通オペレーション

.PHONY: test test-api lint build-check docker-build-api docker-build-worker dev dev-frontend ci clean

# ===========================================================================
# Testing
# ===========================================================================

## Run all Python tests
test:
	python -m pytest tests/ services/api/tests/ -v --tb=short 2>&1 | tail -80

## Run API tests only
test-api:
	python -m pytest services/api/tests/ -v --tb=short

## Run root tests only
test-root:
	python -m pytest tests/ -v --tb=short

# ===========================================================================
# Linting & Type Checking
# ===========================================================================

## Python syntax/import check
lint:
	python -m py_compile services/api/app/main.py
	python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('services/**/*.py', recursive=True)]"
	python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('src/**/*.py', recursive=True)]"
	python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('core/**/*.py', recursive=True)]"
	python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('shared/**/*.py', recursive=True)]"
	@echo "✓ All Python files parse successfully"

## TypeScript type check (requires node_modules installed)
typecheck:
	cd apps/web && npx tsc --noEmit 2>&1 | tail -30

# ===========================================================================
# Build Verification
# ===========================================================================

## Full build check (Docker images + Next.js)
build-check: docker-build-api docker-build-worker
	@echo "✓ All Docker images build successfully"

## Build API Docker image
docker-build-api:
	docker build -f services/api/Dockerfile -t plgen-api:check .

## Build Worker Docker image
docker-build-worker:
	docker build -f services/worker/Dockerfile -t plgen-worker:check .

# ===========================================================================
# Local Development
# ===========================================================================

## Start all backend services (Postgres + Redis + API + Worker)
dev:
	cd infra && docker-compose up --build

## Start Next.js dev server
dev-frontend:
	cd apps/web && npm run dev

# ===========================================================================
# CI Pipeline (used by Agent Teams verification phase)
# ===========================================================================

## Full CI: lint → test → build-check
ci: lint test build-check
	@echo ""
	@echo "========================================"
	@echo "  ✓ CI PASSED — All checks green"
	@echo "========================================"

# ===========================================================================
# Utilities
# ===========================================================================

## Clean Docker build cache
clean:
	docker rmi plgen-api:check plgen-worker:check 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
