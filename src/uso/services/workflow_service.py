"""Workflow service — business logic for DAG workflows."""

from collections import defaultdict, deque

from uso import db
from uso.models import (
    WorkflowCreate,
    WorkflowEdgeOut,
    WorkflowNodeOut,
    WorkflowNodeRunOut,
    WorkflowOut,
    WorkflowRunOut,
)
from uso.services import run_service


def create_workflow(data: WorkflowCreate) -> WorkflowOut:
    wf_id = db.create_workflow(name=data.name, description=data.description)

    # Create nodes first, mapping index → node_id for edge resolution
    node_ids = []
    for node in data.nodes:
        if not db.get_script(node.script_id):
            raise ValueError(f"Script not found: {node.script_id}")
        nid = db.add_node(
            workflow_id=wf_id,
            script_id=node.script_id,
            position_x=node.position_x,
            position_y=node.position_y,
            config=node.config,
        )
        node_ids.append(nid)

    # Create edges (source_node_id/target_node_id reference actual node IDs)
    for edge in data.edges:
        db.add_workflow_edge(
            workflow_id=wf_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            condition=edge.condition,
        )

    return get_workflow(wf_id)


def get_workflow(workflow_id: str) -> WorkflowOut | None:
    row = db.get_workflow(workflow_id)
    if not row:
        return None
    nodes = [WorkflowNodeOut(**n) for n in db.get_nodes(workflow_id)]
    edges = [WorkflowEdgeOut(**e) for e in db.get_workflow_edges(workflow_id)]
    return WorkflowOut(**row, nodes=nodes, edges=edges)


def list_workflows() -> list[WorkflowOut]:
    result = []
    for row in db.list_workflows():
        nodes = [WorkflowNodeOut(**n) for n in db.get_nodes(row["id"])]
        edges = [WorkflowEdgeOut(**e) for e in db.get_workflow_edges(row["id"])]
        result.append(WorkflowOut(**row, nodes=nodes, edges=edges))
    return result


def delete_workflow(workflow_id: str) -> bool:
    existing = db.get_workflow(workflow_id)
    if not existing:
        return False
    db.delete_workflow(workflow_id)
    return True


def add_node(workflow_id: str, script_id: str, position_x: float = 0,
             position_y: float = 0, config: dict | None = None) -> WorkflowNodeOut | None:
    if not db.get_workflow(workflow_id):
        return None
    if not db.get_script(script_id):
        raise ValueError(f"Script not found: {script_id}")
    node_id = db.add_node(workflow_id, script_id, position_x, position_y, config)
    nodes = db.get_nodes(workflow_id)
    return next((WorkflowNodeOut(**n) for n in nodes if n["id"] == node_id), None)


def add_edge(workflow_id: str, source_node_id: str, target_node_id: str,
             condition: dict | None = None) -> WorkflowEdgeOut | None:
    if not db.get_workflow(workflow_id):
        return None
    edge_id = db.add_workflow_edge(workflow_id, source_node_id, target_node_id, condition)
    edges = db.get_workflow_edges(workflow_id)
    return next((WorkflowEdgeOut(**e) for e in edges if e["id"] == edge_id), None)


def _topological_sort(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Return node IDs in topological order (Kahn's algorithm)."""
    node_ids = {n["id"] for n in nodes}
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        src, tgt = edge["source_node_id"], edge["target_node_id"]
        if src in node_ids and tgt in node_ids:
            adjacency[src].append(tgt)
            in_degree[tgt] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adjacency[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(node_ids):
        raise ValueError("Workflow contains a cycle")

    return order


def execute_workflow(
    workflow_id: str,
    env: dict[str, str] | None = None,
    timeout: int = 60,
    on_event=None,
) -> WorkflowRunOut:
    """Execute all nodes in topological order. Stops on first failure.

    Args:
        on_event: optional callback(event_dict) for streaming progress.
    """
    wf = db.get_workflow(workflow_id)
    if not wf:
        raise ValueError("Workflow not found")

    nodes = db.get_nodes(workflow_id)
    edges = db.get_workflow_edges(workflow_id)

    if not nodes:
        raise ValueError("Workflow has no nodes")

    order = _topological_sort(nodes, edges)
    node_map = {n["id"]: n for n in nodes}

    wf_run_id = db.create_workflow_run(workflow_id)
    db.update_workflow_run(wf_run_id, "running")

    # Pre-create all node runs
    node_run_ids: dict[str, str] = {}
    for idx, node_id in enumerate(order):
        nr_id = db.create_node_run(wf_run_id, node_id, idx)
        node_run_ids[node_id] = nr_id

    if on_event:
        on_event({"type": "workflow_start", "workflow_run_id": wf_run_id, "order": order})

    overall_status = "success"

    for idx, node_id in enumerate(order):
        nr_id = node_run_ids[node_id]
        node = node_map[node_id]
        script_id = node["script_id"]

        db.update_node_run(nr_id, "running")
        if on_event:
            on_event({"type": "node_start", "node_id": node_id, "order": idx, "script_id": script_id})

        try:
            run_result = run_service.execute_script(script_id, env=env, timeout=timeout)
            node_status = run_result.status
            db.update_node_run(nr_id, node_status, run_result.id)

            if on_event:
                on_event({
                    "type": "node_complete",
                    "node_id": node_id,
                    "status": node_status,
                    "run_id": run_result.id,
                })

            if node_status not in ("success",):
                overall_status = "failure"
                # Skip remaining nodes
                for remaining_id in order[idx + 1:]:
                    db.update_node_run(node_run_ids[remaining_id], "skipped")
                break
        except Exception:
            db.update_node_run(nr_id, "failure")
            overall_status = "failure"
            if on_event:
                on_event({"type": "node_complete", "node_id": node_id, "status": "failure"})
            for remaining_id in order[idx + 1:]:
                db.update_node_run(node_run_ids[remaining_id], "skipped")
            break

    db.update_workflow_run(wf_run_id, overall_status)
    if on_event:
        on_event({"type": "workflow_complete", "status": overall_status})

    return get_workflow_run(wf_run_id)


def get_workflow_run(workflow_run_id: str) -> WorkflowRunOut | None:
    row = db.get_workflow_run(workflow_run_id)
    if not row:
        return None
    node_runs = [WorkflowNodeRunOut(**nr) for nr in db.get_node_runs(workflow_run_id)]
    return WorkflowRunOut(**row, node_runs=node_runs)


def list_workflow_runs(workflow_id: str) -> list[WorkflowRunOut]:
    result = []
    for row in db.list_workflow_runs(workflow_id):
        node_runs = [WorkflowNodeRunOut(**nr) for nr in db.get_node_runs(row["id"])]
        result.append(WorkflowRunOut(**row, node_runs=node_runs))
    return result
