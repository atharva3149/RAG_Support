# Frontend - Datastraw CX Reply Assistant

React + Vite interface for the Datastraw assessment.

## Working sections

- Inbox conversation view
- Reply assistant (`Generate`, `Regenerate`, `Edit`, `Approve`)
- Conversations list (opens selected conversation)
- Knowledge base view (documents and chunk counts)
- Analytics view (reply log metrics and confidence breakdown)

## Prerequisites

- Node.js 18+
- Backend API running on port `8000` (or configure base URL)

## Environment

Create `frontend/.env.example` if needed:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## Setup and run

```bash
cd frontend
npm install
npm run dev
```

Open:

- App: `http://localhost:5173`
- Backend docs: `http://localhost:8000/docs`

## Build check

```bash
cd frontend
npm run build
```

## Notes

- The app defaults to seeded conversation `maya-patel-broken-bottle`.
- Additional seeded conversations can be opened from `Conversations`.
- If backend is unreachable, UI shows inline error messages.
- Root path `http://localhost:8000/` returns 404 by design; use `/health` or `/docs`.
