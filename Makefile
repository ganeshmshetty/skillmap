SHELL := /bin/bash

.PHONY: up down logs api frontend format install-hooks bootstrap-data

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api:
	cd api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

format:
	cd api && ruff check . --fix && ruff format .

install-hooks:
	pre-commit install

bootstrap-data:
	./scripts/bootstrap_data.sh
