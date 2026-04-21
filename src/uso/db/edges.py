"""Knowledge graph edge CRUD operations."""

import json

from .connection import _gen_id, get_connection


def create_edge(
    source_id: str, target_id: str, relation: str, metadata: dict | None = None
) -> str:
    conn = get_connection()
    edge_id = _gen_id()
    conn.execute(
        "INSERT INTO edges (id, source_id, target_id, relation, metadata) "
        "VALUES (?, ?, ?, ?, ?)",
        (edge_id, source_id, target_id, relation, json.dumps(metadata) if metadata else None),
    )
    conn.commit()
    return edge_id


def get_edge(edge_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM edges WHERE id = ?", (edge_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else None
    return d


def list_edges(script_id: str | None = None) -> list[dict]:
    conn = get_connection()
    if script_id:
        rows = conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ? ORDER BY created_at",
            (script_id, script_id),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM edges ORDER BY created_at").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else None
        result.append(d)
    return result


def delete_edge(edge_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
    conn.commit()
