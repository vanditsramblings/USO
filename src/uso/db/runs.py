"""Run and artifact CRUD operations."""

from .connection import _gen_id, get_connection


def create_run(script_id: str) -> str:
    conn = get_connection()
    run_id = _gen_id()
    conn.execute(
        "INSERT INTO runs (id, script_id, status, start_time) "
        "VALUES (?, ?, 'pending', datetime('now'))",
        (run_id, script_id),
    )
    conn.commit()
    return run_id


def update_run(run_id: str, status: str, exit_code: int | None = None, logs: str = "") -> None:
    conn = get_connection()
    conn.execute(
        """UPDATE runs SET status = ?, exit_code = ?, logs = ?, end_time = datetime('now')
           WHERE id = ?""",
        (status, exit_code, logs, run_id),
    )
    conn.commit()


def get_runs(script_id: str | None = None, limit: int = 50) -> list[dict]:
    conn = get_connection()
    if script_id:
        rows = conn.execute(
            "SELECT * FROM runs WHERE script_id = ? ORDER BY start_time DESC LIMIT ?",
            (script_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY start_time DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --- Artifacts ---


def create_artifact(
    run_id: str, filename: str, path: str, sha256: str | None = None, size_bytes: int | None = None
) -> str:
    conn = get_connection()
    art_id = _gen_id()
    conn.execute(
        "INSERT INTO artifacts (id, run_id, filename, path, sha256, size_bytes)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (art_id, run_id, filename, path, sha256, size_bytes),
    )
    conn.commit()
    return art_id


def get_artifacts(run_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM artifacts WHERE run_id = ? ORDER BY filename", (run_id,)
    ).fetchall()
    return [dict(r) for r in rows]
