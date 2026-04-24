"""Script and parameter CRUD operations."""

from .connection import _gen_id, get_connection


def create_script(name: str, runtime: str, content: str, description: str = "") -> str:
    conn = get_connection()
    script_id = _gen_id()
    conn.execute(
        "INSERT INTO scripts (id, name, runtime, content, description) VALUES (?, ?, ?, ?, ?)",
        (script_id, name, runtime, content, description),
    )
    conn.commit()
    return script_id


def get_script(script_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    return dict(row) if row else None


def get_script_by_name(name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM scripts WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def list_scripts() -> list[dict]:
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM scripts ORDER BY name").fetchall()]


def update_script(script_id: str, content: str, description: str | None = None) -> None:
    conn = get_connection()
    conn.execute(
        """UPDATE scripts SET content = ?, version = version + 1,
           description = COALESCE(?, description), updated_at = datetime('now')
           WHERE id = ?""",
        (content, description, script_id),
    )
    conn.commit()


def delete_script(script_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
    conn.commit()


# --- Parameters ---


def add_parameter(script_id: str, key: str, is_secret: bool = False) -> str:
    conn = get_connection()
    param_id = _gen_id()
    conn.execute(
        "INSERT OR IGNORE INTO parameters (id, script_id, key, is_secret) VALUES (?, ?, ?, ?)",
        (param_id, script_id, key, int(is_secret)),
    )
    conn.commit()
    return param_id


def get_parameters(script_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM parameters WHERE script_id = ? ORDER BY key", (script_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def delete_parameter(param_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM parameters WHERE id = ?", (param_id,))
    conn.commit()
