"""Schedule CRUD operations."""

from .connection import _gen_id, get_connection


def create_schedule(
    script_id: str, trigger_type: str, trigger_args: str, misfire_grace_time: int = 60
) -> str:
    conn = get_connection()
    schedule_id = _gen_id()
    conn.execute(
        "INSERT INTO schedules (id, script_id, trigger_type, trigger_args, misfire_grace_time)"
        " VALUES (?, ?, ?, ?, ?)",
        (schedule_id, script_id, trigger_type, trigger_args, misfire_grace_time),
    )
    conn.commit()
    return schedule_id


def get_schedule(schedule_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    return dict(row) if row else None


def list_schedules(script_id: str | None = None) -> list[dict]:
    conn = get_connection()
    if script_id:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE script_id = ? ORDER BY created_at", (script_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM schedules ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


def update_schedule_enabled(schedule_id: str, enabled: bool) -> None:
    conn = get_connection()
    conn.execute("UPDATE schedules SET enabled = ? WHERE id = ?", (int(enabled), schedule_id))
    conn.commit()


def delete_schedule(schedule_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
