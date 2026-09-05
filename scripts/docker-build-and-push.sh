#!/usr/bin/env bash
set -euo pipefail

# Build and push Docker images for frontend and backend.
# Requires: DOCKER_REGISTRY (default: docker.io), DOCKER_USER, DOCKER_REPO, TAG (optional)

REGISTRY=${DOCKER_REGISTRY:-docker.io}
USER=${DOCKER_USER:-}
REPO=${DOCKER_REPO:-datastraw}
TAG=${TAG:-latest}

if [ -z "$USER" ]; then
  echo "Please set DOCKER_USER environment variable (your Docker Hub username or registry user)." >&2
  exit 1
fi

BACKEND_IMAGE="$REGISTRY/$USER/$REPO-backend:$TAG"
FRONTEND_IMAGE="$REGISTRY/$USER/$REPO-frontend:$TAG"

echo "Building backend image: $BACKEND_IMAGE"
docker build -t "$BACKEND_IMAGE" -f backend/Dockerfile .

echo "Building frontend image: $FRONTEND_IMAGE"
docker build -t "$FRONTEND_IMAGE" -f frontend/Dockerfile .

echo "Pushing images to $REGISTRY"
docker push "$BACKEND_IMAGE"
docker push "$FRONTEND_IMAGE"

echo "Images pushed successfully. Use these image references in your deployment platform."
