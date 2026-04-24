# ── Stage 1: Build SvelteKit frontend ────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Install Python dependencies ─────────────────────────────────────
FROM python:3.12-slim AS py-builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 3: Runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim

RUN useradd -m -r -u 1001 appuser

WORKDIR /app

# Copy installed Python packages and their console scripts
COPY --from=py-builder /install /usr/local

# Copy application source
COPY src/ src/
COPY scripts/ scripts/

# Copy built frontend into location FastAPI serves it from
COPY --from=frontend-builder /frontend/build/ frontend/build/

# Writable data directories owned by the non-root user
RUN mkdir -p data/outputs data/uploads && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "uso.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
