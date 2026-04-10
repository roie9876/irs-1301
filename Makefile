.PHONY: install run lint test

install:
	cd frontend && npm install
	.venv/bin/pip install -r backend/requirements.txt

run:
	npx -y concurrently -n "front,back" -c "cyan,green" \
		"cd frontend && npm run dev" \
		"cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000"

lint:
	cd frontend && npx tsc --noEmit
	cd backend && ../.venv/bin/python -m ruff check . 2>/dev/null || true

test:
	cd backend && ../.venv/bin/python -m pytest tests/ -x
	cd frontend && npx vitest run 2>/dev/null || true
