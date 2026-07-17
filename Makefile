.PHONY: bootstrap backend frontend test lint up down security tree
bootstrap:
	cp -n .env.example .env || true
	python -m venv .venv
	. .venv/bin/activate && pip install -e "./backend[dev]"
backend:
	cd backend && uvicorn app.main:app --reload
frontend:
	cd frontend && npm ci && npm run dev
test:
	cd backend && pytest
lint:
	cd backend && ruff check app tests && mypy app
	cd frontend && npm run typecheck
up:
	docker compose up --build
down:
	docker compose down
security:
	bash scripts/run_security_checks.sh
tree:
	python scripts/generate_tree.py
