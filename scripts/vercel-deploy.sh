#!/usr/bin/env bash
set -euo pipefail

# Deploy frontend and backend to Vercel using the Vercel CLI.
# Requirements:
# - vercel CLI installed (`npm i -g vercel`) or use `npx vercel`
# - VERCEL_TOKEN env var set (or be logged in with `vercel login`)
# - Set required environment variables in Vercel dashboard (DATABASE_URL, OPENROUTER_API_KEY, etc.)

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "VERCEL_TOKEN is not set. Export it or login with 'vercel login' and try again." >&2
  exit 1
fi

echo "Deploying frontend to Vercel..."
vercel --prod frontend --token "$VERCEL_TOKEN" --confirm

echo "Deploying backend to Vercel..."
# backend contains a Dockerfile; Vercel will use it to build your service.
vercel --prod backend --token "$VERCEL_TOKEN" --confirm

echo "Deployment requests submitted."
echo "Note: Configure runtime environment variables for the backend in the Vercel dashboard or with 'vercel env' before visiting the backend deployment."

echo "Recommended runtime envs: DATABASE_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL"
