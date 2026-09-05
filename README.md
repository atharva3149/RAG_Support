# Relaydesk: CX Reply Assistant

Small full-stack assessment app for Datastraw's Part 1 build. It helps a CX agent open a conversation, retrieve brand policy context, generate a grounded draft, and approve a final response.

## Repositories and docs

- `backend/README.md`: backend setup, env vars, APIs, and validation.
- `frontend/README.md`: frontend setup and usage.
- `docs/HOW_IT_WORKS.md`: runtime flow and orchestration.
- `docs/PROJECT_STRUCTURE.md`: cleaned folder structure.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Psycopg, Pydantic Settings
- Database: PostgreSQL + pgvector
- Retrieval: local `sentence-transformers/all-MiniLM-L6-v2`
- LLM: OpenRouter with guarded fallback behavior

## Main features

- Conversation view with customer, brand, order, and message history
- Knowledge-base-backed reply generation
- Edit, regenerate, and approve reply flow
- Guardrails for refund promises and weak retrieval cases
- Analytics from reply logs
- Multiple seeded test conversations for demo coverage

## Quick start

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
set -a && . .env && set +a
psql "$DATABASE_URL" -f migrations/001_initial.sql
python -m scripts.seed
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Seeded scenarios

- `maya-patel-broken-bottle`
- `arjun-mehta-refund-after-20-days`
- `sara-kim-ship-to-canada`
- `leo-fernandez-gift-wrapping`
