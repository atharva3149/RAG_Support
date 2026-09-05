# Project Structure

## Root

- `backend/`: FastAPI API, seed scripts, database migration, tests.
- `frontend/`: React + Vite agent UI.
- `docs/`: supporting documentation.

## Backend

- `app/api/`: HTTP endpoints.
- `app/core/`: settings and DB connection.
- `app/models/`: API request/response models.
- `app/repositories/`: tenant-scoped SQL access.
- `app/services/`: embeddings, generation, guardrails.
- `scripts/`: local data seeding.
- `tests/`: unit tests.
- `migrations/`: schema DDL.

## Frontend

- `src/App.tsx`: main workspace screen.
- `src/api.ts`: backend client.
- `src/types.ts`: shared frontend API types.
- `src/styles.css`: page styling.