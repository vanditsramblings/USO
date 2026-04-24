# USO — Unified Script Orchestrator

> Centralized, secure, and observable script management across Python, Shell, and JavaScript runtimes.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](#)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)](#)
[![SvelteKit](https://img.shields.io/badge/frontend-SvelteKit-FF3E00)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#)

---

## What is USO?

USO is a self-hosted platform for organizing, executing, and monitoring scripts across multiple runtimes from a single UI. It provides a tag-based script inventory, real-time execution logs, encrypted secrets, workflow chaining, scheduling, and a live dependency graph — all accessible through a modern SvelteKit interface backed by a FastAPI + SQLite server.

**Key use cases**

- Automate repetitive dev-ops or data-pipeline tasks without leaving a browser
- Chain scripts into multi-step workflows with file and env-variable passing
- Run and monitor scripts on demand or on a schedule
- Inspect execution history and metrics in the built-in dashboard

---

## Features

| Capability | Description |
|---|---|
| **Script Registry** | Register and version py / sh / js scripts with full parameter metadata |
| **Tag-based Filtering** | Capability, language, and intent tags with live filter chips |
| **Workflow Chaining** | Visual multi-step workflows with configurable node env vars |
| **Dependency Graph** | D3 force graph showing script→workflow edges |
| **Secure Secrets** | Fernet-encrypted environment variables injected at runtime |
| **Real-time Logs** | Stream stdout/stderr to the UI via WebSocket during execution |
| **Scheduler** | APScheduler-backed cron and interval triggers |
| **Metrics Dashboard** | Success/failure rates and per-script execution breakdowns |
| **MCP Server** | FastMCP integration for AI-agent tool use |
| **Docker Ready** | Multi-stage Dockerfile + docker compose for one-command deploy |

---

## Quick Start

### Local (recommended for development)

```bash
git clone <repo-url> && cd uso
./start.sh
# Open http://localhost:8000
```

`start.sh` creates a virtualenv, installs Python deps, builds the SvelteKit frontend, and launches `uvicorn` — all in one step.

For frontend hot-reload during UI development:

```bash
./start.sh --dev
# Backend: http://localhost:8000
# Frontend dev server: http://localhost:5173
```

### Docker

```bash
# Build and run (requires Docker 24+)
docker compose up --build

# Or run without compose
docker build -t uso .
docker run -p 8000:8000 -e USO_MASTER_KEY=<key> uso
```

App is available at **http://localhost:8000**.

---

## Configuration

| Env var | Default | Description |
|---|---|---|
| `USO_MASTER_KEY` | — | Fernet key for secret encryption (required for secrets) |
| `USO_DB_PATH` | `data/uso.db` | SQLite database path |
| `USO_LOG_LEVEL` | `INFO` | Logging verbosity |

Generate a master key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Demo Scripts

USO ships with 9 curated scripts covering file I/O, env chaining, network calls, metrics, and multi-language execution.

| Script | Runtime | Tags | Purpose |
|---|---|---|---|
| `health_check` | Python | `network` `monitoring` `demo` | Call `/health` and print a formatted report |
| `file_generator_demo` | Python | `file` `demo` | Generate JSON, CSV, YAML, and HTML output files |
| `env_chain_demo` | Shell | `demo` `automation` | Read, transform, and forward env variables between steps |
| `metrics_export` | Python | `metrics` `reporting` `network` | Fetch `/api/metrics` and export to CSV |
| `process_metrics_csv` | Shell | `metrics` `reporting` `file` | Summarise a metrics CSV in the terminal |
| `api_client_demo` | JavaScript | `network` `integration` `demo` | Query the USO API and display the script inventory |
| `list_scripts` | Python | `utility` `network` | List all registered scripts via the API |
| `system_info` | Shell | `utility` `system` | Print OS, CPU, memory, and disk information |
| `echo_times` | Shell | `demo` `utility` | Echo a message N times — demonstrates parameter passing |

---

## Demo Workflows

Three built-in workflows demonstrate the core chaining patterns.

### 1. Metrics-Pipeline-Demo
**File output chaining** — exports metrics to CSV, then summarises the file.

```
metrics_export  ──▶  process_metrics_csv
```

### 2. File-Output-Chain
**File generation + env handoff** — generates structured output files, then reads the generated path via env vars.

```
file_generator_demo  ──▶  env_chain_demo
```

### 3. API-Probe-Chain
**Network verification + inventory** — verifies the app is healthy, then queries and displays the script inventory.

```
health_check  ──▶  api_client_demo
```

---

## Architecture

```
src/uso/
  api/app.py          # FastAPI application factory + lifespan
  api/routes/         # REST + WebSocket route handlers
  db/                 # SQLite CRUD layer (scripts, runs, tags, workflows, edges…)
  services/           # Business logic layer
  executor.py         # Subprocess execution with resource limits
  scheduler.py        # APScheduler integration
  secret_manager.py   # Fernet encrypt/decrypt
  seed.py             # Database seeding (scripts, tags, workflows)
  mcp_server.py       # FastMCP server for AI-agent use

frontend/src/
  routes/             # SvelteKit page routes (scripts, graph, metrics, schedules…)
  components/         # Shared UI components (OmniSearch, ScriptFlyout, Sidebar…)
  stores/             # Svelte 5 runes-based state stores

scripts/predefined/   # Demo script source files
data/                 # SQLite DB and script output artifacts (gitignored)
```

**Request path:** SvelteKit page → `/api/*` or `/ws/*` route → service layer → SQLite (WAL mode)

---

## Development

```bash
make install    # Create venv + install Python deps
make test       # Run pytest (107 tests)
make lint       # Run ruff check + format check
./start.sh --dev  # Backend (port 8000) + frontend dev server (port 5173)
```

**Tech stack**

- Backend: Python 3.12, FastAPI, uvicorn, APScheduler 3.11, SQLite WAL
- Frontend: SvelteKit 5 (runes), Tailwind CSS v4, Lucide icons, D3
- Security: Fernet encryption, non-root Docker user, CORS-scoped origins

---

## Testing

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
```

Test modules cover: API routes, DB layer, executor, detector, file manager, scheduler, MCP server, secret manager, graph API, and service layer.

---

## License

MIT

