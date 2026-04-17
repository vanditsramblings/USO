#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

VENV=".venv"

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi

# Install dependencies
echo "Installing dependencies..."
"$VENV/bin/pip" install -e ".[dev]" --quiet

# Copy .env if missing
if [ ! -f .env ]; then
    echo "Copying .env.example → .env (fill in your values)"
    cp .env.example .env
fi

# Create data directories
mkdir -p data/outputs data/uploads

echo "Starting USO..."
"$VENV/bin/streamlit" run app.py
