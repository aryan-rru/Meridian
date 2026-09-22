.PHONY: up down logs migrate revision seed reset backend frontend install test test-backend test-frontend lint fmt

# ---------------------------------------------------------------------------
# Docker (Postgres + backend + frontend)
# ---------------------------------------------------------------------------
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

db-only:
	docker compose up -d db

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
migrate:
	cd backend && alembic upgrade head

revision:
	cd backend && alembic revision --autogenerate -m "$(m)"

seed:
	cd backend && python -m app.seed

reset:
	cd backend && python -m app.seed --reset

# ---------------------------------------------------------------------------
# Local dev (outside docker)
# ---------------------------------------------------------------------------
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
test: test-backend test-frontend

test-backend:
	cd backend && pytest -q

test-frontend:
	cd frontend && npm run test -- --run

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

fmt:
	cd backend && ruff check --fix app tests && black app tests
	cd frontend && npm run format
