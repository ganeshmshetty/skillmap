# AI-Adaptive Onboarding Engine

Initial bootstrap for the hackathon project described in `execution_plan.html`.

## Monorepo Structure

```text
.
├── api/                  # FastAPI backend
├── frontend/             # React + Vite frontend
├── data/                 # Datasets and generated artifacts
├── scripts/              # Utility scripts (data/bootstrap)
├── docker-compose.yml    # Local dev stack (api + frontend + redis)
├── .env.example          # Environment template
└── .pre-commit-config.yaml
```

## What Is Already Set Up

- `api` service with starter endpoints:
	- `GET /health`
	- `POST /analyze` (accepts resume + JD files, returns `job_id`)
	- `GET /result/{job_id}`
- `frontend` service with a minimal upload UI wired to backend endpoints.
- `redis` service included in Docker Compose.
- Pre-commit hooks (`ruff`, formatting, whitespace/yaml/json checks).
- Workspace extension recommendations in `.vscode/extensions.json`.

## Quick Start

1. Create local env file:

```bash
cp .env.example .env
```

2. Start everything:

```bash
docker compose up --build
```

3. Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

## Local (Without Docker)

### Backend

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Next Build Steps (Phase 1)

- Resume/JD parsing for PDF/DOCX/plain text.
- O*NET skill anchoring and semantic matching.
- Redis-backed async job queue and SSE progress streaming.
- Course catalog + prerequisite DAG traversal engine.