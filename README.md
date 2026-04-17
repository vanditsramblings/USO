# USO — Unified Script Orchestrator

A centralized, secure, and observable platform for managing scripts across Python, Shell, and JavaScript runtimes.

## Quick Start

```bash
# Clone and run
git clone <repo-url> && cd uso
./start.sh
```

Or with Docker:
```bash
docker compose up
```

## Features

| Capability | Description |
|---|---|
| **Script Registry** | Register, version, and manage py/sh/js scripts in SQLite |
| **Secure Secrets** | Fernet-encrypted environment variables, injected at runtime |
| **Resource Limits** | CPU, memory, and file-size constraints via OS-level controls |
| **Real-time Logs** | Stream stdout/stderr to the UI during execution |
| **Metrics Dashboard** | Success/failure rates, per-script breakdowns, recent runs |
| **Docker Ready** | Multi-stage Dockerfile + docker-compose for one-click deploy |

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `USO_MASTER_KEY` | — | Fernet key for secret encryption (required) |
| `USO_DB_PATH` | `data/uso.db` | SQLite database location |
| `USO_LOG_LEVEL` | `INFO` | Logging verbosity |

## Architecture

```
src/uso/
  db.py              # SQLite layer (WAL mode, CRUD)
  secret_manager.py  # Fernet encrypt/decrypt
  executor.py        # SubprocessExecutor with resource limits
app.py               # Streamlit entry point
pages/
  1_Library.py       # Script registration & management
  2_Execute.py       # Run scripts with real-time logs
  3_Metrics.py       # Dashboard charts
tests/               # pytest suite
```

## Development

```bash
make install    # Create venv + install deps
make test       # Run pytest
make lint       # Run ruff
make dev        # Install + launch Streamlit
```

## License

MIT
