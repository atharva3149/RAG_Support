#!/usr/bin/env bash
set -euo pipefail
# Run backend in background, then run frontend in foreground. Kills backend when frontend exits.
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# load env file if present
if [ -f backend/.env ]; then
  set -a
  . backend/.env
  set +a
fi

# ensure previous backend on :8000 is stopped, then start backend in background from backend/ directory
kill $(lsof -ti :8000) 2>/dev/null || true
(
  cd "$ROOT_DIR/backend"
  . .venv/bin/activate 2>/dev/null || true
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
BACK_PID=$!

echo "Started backend (PID=$BACK_PID). Starting frontend..."

cd "$ROOT_DIR/frontend"
npm run dev

# frontend exited — shut down backend
echo "Frontend exited; shutting down backend (PID=$BACK_PID)"
kill "$BACK_PID" 2>/dev/null || true
