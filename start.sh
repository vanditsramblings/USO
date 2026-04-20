#!/usr/bin/env bash
# USO — single start script
# Usage: ./start.sh [--dev] [--skip-build]
#   --dev         run frontend dev server (port 5173) alongside backend
#   --skip-build  skip npm build (use existing frontend/build/)
set -e
cd "$(dirname "$0")"

VENV=".venv"
DEV_MODE=false
SKIP_BUILD=false

for arg in "$@"; do
  case $arg in
    --dev) DEV_MODE=true ;;
    --skip-build) SKIP_BUILD=true ;;
  esac
done

# ── Python virtualenv ──────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
  echo "▶ Creating virtual environment..."
  python3 -m venv "$VENV"
fi

echo "▶ Installing Python dependencies..."
"$VENV/bin/pip" install -e ".[dev]" --quiet

# ── .env ───────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "▶ Copying .env.example → .env"
  cp .env.example .env
fi

# ── Data directories ───────────────────────────────────────────────
mkdir -p data/outputs data/uploads

# ── Frontend build ─────────────────────────────────────────────────
if [ "$SKIP_BUILD" = false ]; then
  if command -v npm &>/dev/null; then
    echo "▶ Building frontend..."
    cd frontend
    npm ci --silent
    npm run build
    cd ..
  else
    echo "⚠  npm not found — skipping frontend build. Install Node.js to build the UI."
  fi
fi

# ── Start ──────────────────────────────────────────────────────────
if [ "$DEV_MODE" = true ]; then
  echo "▶ Starting backend (port 8000) + frontend dev server (port 5173)..."
  cd frontend && npm run dev &
  cd "$(dirname "$0")"
  "$VENV/bin/uvicorn" uso.api.app:create_app \
    --factory --reload --host 0.0.0.0 --port 8000
else
  echo "▶ Starting USO on http://localhost:8000 ..."
  "$VENV/bin/uvicorn" uso.api.app:create_app \
    --factory --host 0.0.0.0 --port 8000
fi
