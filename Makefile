.PHONY: setup up down logs migrate seed test lint format reset

setup:
	cp -n .env.example .env || true

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.seed

test:
	docker compose exec backend pytest
	cd frontend && npm test -- --run

lint:
	docker compose exec backend ruff check app tests
	docker compose exec backend mypy app
	cd frontend && npm run lint

format:
	docker compose exec backend ruff format app tests
	cd frontend && npm run format

reset:
	docker compose down -v
	docker compose up --build
