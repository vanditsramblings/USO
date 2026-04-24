"""SQLite connection management, schema, and initialization."""

import sqlite3
import threading
import uuid
from pathlib import Path

_local = threading.local()

DEFAULT_DB_PATH = Path("data/uso.db")


def _gen_id() -> str:
    return str(uuid.uuid4())


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scripts (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    runtime TEXT NOT NULL CHECK (runtime IN ('sh', 'py', 'js')),
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS parameters (
    id TEXT PRIMARY KEY,
    script_id TEXT NOT NULL,
    key TEXT NOT NULL,
    is_secret BOOLEAN DEFAULT 0,
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
    UNIQUE(script_id, key)
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    script_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending','running','success','failure','timeout')),
    start_time TEXT, end_time TEXT, exit_code INTEGER, logs TEXT,
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    filename TEXT NOT NULL, path TEXT NOT NULL,
    sha256 TEXT, size_bytes INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    script_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('cron', 'interval', 'date')),
    trigger_args TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    misfire_grace_time INTEGER DEFAULT 60,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS script_tags (
    script_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (script_id, tag_id),
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL CHECK (relation IN ('data_flow','shared_env','manual','sequential')),
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES scripts(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES scripts(id) ON DELETE CASCADE,
    UNIQUE(source_id, target_id, relation)
);
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    script_id TEXT NOT NULL,
    position_x REAL DEFAULT 0,
    position_y REAL DEFAULT 0,
    config TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
    FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS workflow_edges (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    condition TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    UNIQUE(source_node_id, target_node_id)
);
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending','running','success','failure')),
    started_at TEXT DEFAULT (datetime('now')),
    finished_at TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS workflow_node_runs (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    run_id TEXT,
    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending','running','success','failure','skipped')),
    execution_order INTEGER NOT NULL,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Get a thread-local SQLite connection with WAL mode."""
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    key = str(db_path)
    if not hasattr(_local, "connections"):
        _local.connections = {}
    if key not in _local.connections:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        _local.connections[key] = conn
    return _local.connections[key]


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize database schema."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
