# USO Database Schema Reference
> Auto-maintained. Matches `src/uso/db.py` SCHEMA_SQL.

## Tables

### `scripts`
| Column | Type | Constraint | Description |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique script identifier |
| name | TEXT | UNIQUE, NOT NULL | Human-readable name for discovery |
| runtime | TEXT | NOT NULL, CHECK (sh/py/js) | Execution environment |
| content | BLOB | NOT NULL | Script source code |
| version | INTEGER | DEFAULT 1 | Incremented on each update |
| description | TEXT | NULLABLE | Documentation / MCP discovery text |
| created_at | TEXT | DEFAULT datetime('now') | Registration timestamp |
| updated_at | TEXT | DEFAULT datetime('now') | Last modification timestamp |

### `parameters`
| Column | Type | Constraint | Description |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Parameter identifier |
| script_id | INTEGER | FK → scripts(id) CASCADE | Owning script |
| key | TEXT | NOT NULL | Environment variable name |
| is_secret | BOOLEAN | DEFAULT 0 | Triggers Fernet encryption |
| | | UNIQUE(script_id, key) | No duplicate keys per script |

### `runs`
| Column | Type | Constraint | Description |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Run identifier |
| script_id | INTEGER | FK → scripts(id) CASCADE | Executed script |
| status | TEXT | DEFAULT 'pending' | pending/running/success/failure/timeout |
| start_time | TEXT | | ISO timestamp |
| end_time | TEXT | | ISO timestamp |
| exit_code | INTEGER | | Process exit code |
| logs | TEXT | | Captured stdout + stderr |

### `artifacts`
| Column | Type | Constraint | Description |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Artifact identifier |
| run_id | INTEGER | FK → runs(id) CASCADE | Producing run |
| filename | TEXT | NOT NULL | Original filename |
| path | TEXT | NOT NULL | Storage path |
| sha256 | TEXT | | Content hash |
| size_bytes | INTEGER | | File size |
| created_at | TEXT | DEFAULT datetime('now') | Creation timestamp |

## Pragmas
- `journal_mode = WAL` — concurrent reads during writes
- `synchronous = NORMAL` — balanced durability/performance
- `foreign_keys = ON` — enforce referential integrity
