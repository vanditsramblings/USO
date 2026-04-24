"""Workflow (DAG) CRUD operations."""

import json

from .connection import _gen_id, get_connection


def create_workflow(name: str, description: str = "") -> str:
    conn = get_connection()
    wf_id = _gen_id()
    conn.execute(
        "INSERT INTO workflows (id, name, description) VALUES (?, ?, ?)",
        (wf_id, name, description),
    )
    conn.commit()
    return wf_id


def get_workflow(workflow_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
    return dict(row) if row else None


def list_workflows() -> list[dict]:
    conn = get_connection()
    return [dict(r) for r in conn.execute("SELECT * FROM workflows ORDER BY name").fetchall()]


def delete_workflow(workflow_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    conn.commit()


# --- Workflow Nodes ---


def add_node(
    workflow_id: str,
    script_id: str,
    position_x: float = 0,
    position_y: float = 0,
    config: dict | None = None,
) -> str:
    conn = get_connection()
    node_id = _gen_id()
    conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, script_id, position_x, position_y, config) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (node_id, workflow_id, script_id, position_x, position_y,
         json.dumps(config) if config else None),
    )
    conn.commit()
    return node_id


def get_nodes(workflow_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM workflow_nodes WHERE workflow_id = ?", (workflow_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"]) if d["config"] else None
        result.append(d)
    return result


def delete_node(node_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM workflow_nodes WHERE id = ?", (node_id,))
    conn.commit()


def update_node(node_id: str, position_x: float | None, position_y: float | None,
                config: dict | None) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM workflow_nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        return None
    current = dict(row)
    new_x = position_x if position_x is not None else current["position_x"]
    new_y = position_y if position_y is not None else current["position_y"]
    # config=None means "keep current"; pass {} explicitly to clear
    new_config = json.dumps(config) if config is not None else current["config"]
    conn.execute(
        "UPDATE workflow_nodes SET position_x = ?, position_y = ?, config = ? WHERE id = ?",
        (new_x, new_y, new_config, node_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM workflow_nodes WHERE id = ?", (node_id,)).fetchone()
    d = dict(updated)
    d["config"] = json.loads(d["config"]) if d["config"] else None
    return d


# --- Workflow Edges ---


def add_workflow_edge(
    workflow_id: str,
    source_node_id: str,
    target_node_id: str,
    condition: dict | None = None,
) -> str:
    conn = get_connection()
    edge_id = _gen_id()
    conn.execute(
        "INSERT INTO workflow_edges (id, workflow_id, source_node_id, target_node_id, condition) "
        "VALUES (?, ?, ?, ?, ?)",
        (edge_id, workflow_id, source_node_id, target_node_id,
         json.dumps(condition) if condition else None),
    )
    conn.commit()
    return edge_id


def get_workflow_edges(workflow_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM workflow_edges WHERE workflow_id = ?", (workflow_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["condition"] = json.loads(d["condition"]) if d["condition"] else None
        result.append(d)
    return result


def delete_workflow_edge(edge_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM workflow_edges WHERE id = ?", (edge_id,))
    conn.commit()


# --- Workflow Runs ---


def create_workflow_run(workflow_id: str) -> str:
    conn = get_connection()
    run_id = _gen_id()
    conn.execute(
        "INSERT INTO workflow_runs (id, workflow_id, status) VALUES (?, ?, 'pending')",
        (run_id, workflow_id),
    )
    conn.commit()
    return run_id


def update_workflow_run(run_id: str, status: str) -> None:
    conn = get_connection()
    if status in ("success", "failure"):
        conn.execute(
            "UPDATE workflow_runs SET status = ?, finished_at = datetime('now') WHERE id = ?",
            (status, run_id),
        )
    else:
        conn.execute(
            "UPDATE workflow_runs SET status = ? WHERE id = ?",
            (status, run_id),
        )
    conn.commit()


def get_workflow_run(run_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def list_workflow_runs(workflow_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM workflow_runs WHERE workflow_id = ? ORDER BY started_at DESC",
        (workflow_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Workflow Node Runs ---


def create_node_run(workflow_run_id: str, node_id: str, execution_order: int) -> str:
    conn = get_connection()
    nr_id = _gen_id()
    conn.execute(
        "INSERT INTO workflow_node_runs (id, workflow_run_id, node_id, status, execution_order) "
        "VALUES (?, ?, ?, 'pending', ?)",
        (nr_id, workflow_run_id, node_id, execution_order),
    )
    conn.commit()
    return nr_id


def update_node_run(node_run_id: str, status: str, run_id: str | None = None) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE workflow_node_runs SET status = ?, run_id = ? WHERE id = ?",
        (status, run_id, node_run_id),
    )
    conn.commit()


def get_node_runs(workflow_run_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM workflow_node_runs WHERE workflow_run_id = ? ORDER BY execution_order",
        (workflow_run_id,),
    ).fetchall()
    return [dict(r) for r in rows]
