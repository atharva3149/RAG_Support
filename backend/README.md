# Backend - Datastraw CX Reply Assistant

FastAPI backend for Part 1 of the Datastraw assessment.

## What this backend provides

- Conversation APIs for inbox and conversation list
- Retrieval-augmented reply generation
- Policy guardrails for risky refund promises
- Reply log approval and audit trails
- Knowledge base and analytics APIs
- Clean package structure under `app/api`, `app/core`, `app/models`, `app/repositories`, and `app/services`

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- `pgvector` extension available in Postgres

## Environment

Create `backend/.env` from `backend/.env.example`.

```dotenv
DATABASE_URL=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=minimax/minimax-m3:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FRONTEND_ORIGIN=http://localhost:5173
SIMILARITY_THRESHOLD=0.35
SIMILARITY_MIN_MARGIN=0.02
SIMILARITY_STRONG_MATCH_THRESHOLD=0.55
```

## Setup and run

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Apply schema and seed data:

```bash
cd backend
set -a && . .env && set +a
psql "$DATABASE_URL" -f migrations/001_initial.sql
python -m scripts.seed
```

Run API (recommended for lower memory):

```bash
cd backend
. .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run with auto-reload (dev convenience, higher memory):

```bash
cd backend
. .venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## OOM troubleshooting (exit 137)

If the process is killed (often due to memory pressure):

- Run without `--reload`
- Check OOM logs:

```bash
dmesg -T | grep -i -E 'killed process|oom' | tail -n 50
```

- Check memory:

```bash
free -h
```

## Retrieval confidence calibration

Generation is gated by a confidence rule:

- top similarity must be `>= SIMILARITY_THRESHOLD`
- and either:
	- `top_similarity - second_similarity >= SIMILARITY_MIN_MARGIN`, or
	- `top_similarity >= SIMILARITY_STRONG_MATCH_THRESHOLD`

Defaults are tuned for this seeded policy dataset. Recalibrate when your knowledge base grows.

## API endpoints

- `GET /health`
- `GET /api/conversations`
- `GET /api/conversations/by-slug/{slug}`
- `GET /api/conversations/{conversation_id}`
- `POST /api/conversations/{conversation_id}/generate`
- `POST /api/conversations/{conversation_id}/reply-logs/{log_id}/approve`
- `GET /api/brands/{brand_id}/knowledge-documents`
- `GET /api/brands/{brand_id}/analytics`

## Backend package layout

```text
backend/app/
├── api/
├── core/
├── models/
├── repositories/
├── services/
└── main.py
```

Compatibility shim modules remain at the top level of `app/` so existing imports still work while the codebase uses the cleaned package layout.

## Verify

```bash
cd backend
. .venv/bin/activate
pytest -q
curl http://localhost:8000/health
```
