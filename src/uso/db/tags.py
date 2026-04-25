"""Tag CRUD operations."""

from .connection import _gen_id, get_connection


def create_tag(name: str) -> str:
    conn = get_connection()
    tag_id = _gen_id()
    conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (tag_id, name))
    conn.commit()
    return tag_id


def get_tag(tag_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone()
    return dict(row) if row else None


def get_tag_by_name(name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM tags WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def list_tags() -> list[dict]:
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM tags ORDER BY name").fetchall()]


def delete_tag(tag_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()


def tag_script(script_id: str, tag_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO script_tags (script_id, tag_id) VALUES (?, ?)",
        (script_id, tag_id),
    )
    conn.commit()


def untag_script(script_id: str, tag_id: str) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM script_tags WHERE script_id = ? AND tag_id = ?",
        (script_id, tag_id),
    )
    conn.commit()


def get_script_tags(script_id: str) -> list[dict]:
    conn = get_connection()
    return [
        dict(r)
        for r in conn.execute(
            "SELECT t.* FROM tags t JOIN script_tags st ON t.id = st.tag_id "
            "WHERE st.script_id = ? ORDER BY t.name",
            (script_id,),
        ).fetchall()
    ]


def get_scripts_by_tag(tag_id: str) -> list[str]:
    conn = get_connection()
    return [
        r["script_id"]
        for r in conn.execute(
            "SELECT script_id FROM script_tags WHERE tag_id = ?", (tag_id,)
        ).fetchall()
    ]


def get_tags_for_scripts(script_ids: list[str]) -> dict[str, list[dict]]:
    """Return a mapping of script_id → list of tag dicts for all given script IDs.
    Uses a single query instead of one per script."""
    if not script_ids:
        return {}
    placeholders = ",".join("?" * len(script_ids))
    conn = get_connection()
    rows = conn.execute(
        f"SELECT st.script_id, t.id, t.name, t.created_at "
        f"FROM tags t JOIN script_tags st ON t.id = st.tag_id "
        f"WHERE st.script_id IN ({placeholders}) ORDER BY t.name",
        script_ids,
    ).fetchall()
    result: dict[str, list[dict]] = {sid: [] for sid in script_ids}
    for row in rows:
        result[row["script_id"]].append(
            {"id": row["id"], "name": row["name"], "created_at": row["created_at"]}
        )
    return result
