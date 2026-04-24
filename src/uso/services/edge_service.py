"""Edge service — business logic for knowledge graph edges."""

from uso import db
from uso.models import EdgeCreate, EdgeOut


def create_edge(data: EdgeCreate) -> EdgeOut:
    # Validate both scripts exist
    if not db.get_script(data.source_id):
        raise ValueError(f"Source script not found: {data.source_id}")
    if not db.get_script(data.target_id):
        raise ValueError(f"Target script not found: {data.target_id}")
    if data.source_id == data.target_id:
        raise ValueError("Self-edges are not allowed")

    edge_id = db.create_edge(
        source_id=data.source_id,
        target_id=data.target_id,
        relation=data.relation.value,
        metadata=data.metadata,
    )
    return get_edge(edge_id)


def get_edge(edge_id: str) -> EdgeOut | None:
    row = db.get_edge(edge_id)
    return EdgeOut(**row) if row else None


def list_edges(script_id: str | None = None) -> list[EdgeOut]:
    return [EdgeOut(**r) for r in db.list_edges(script_id)]


def delete_edge(edge_id: str) -> bool:
    existing = db.get_edge(edge_id)
    if not existing:
        return False
    db.delete_edge(edge_id)
    return True
