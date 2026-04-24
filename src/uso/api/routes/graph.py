"""Graph data endpoint — returns nodes and edges for the knowledge graph."""

from fastapi import APIRouter

from uso import db
from uso.services.script_service import list_scripts
from uso.services.tag_service import list_tags, get_script_tags
from uso.services.edge_service import list_edges

router = APIRouter()


@router.get("")
def get_graph():
    """Build full knowledge graph: script, tag, and language nodes + all edge types."""
    scripts = list_scripts()
    tags = list_tags()
    edges = list_edges()

    nodes = []
    graph_edges = []

    # Language hub nodes
    runtimes_seen: set[str] = set()

    for s in scripts:
        # Last run status
        runs = db.get_runs(script_id=s.id, limit=1)
        last_status = runs[0]["status"] if runs else None

        nodes.append(
            {
                "id": s.id,
                "type": "script",
                "data": {
                    "name": s.name,
                    "runtime": s.runtime,
                    "lastStatus": last_status,
                    "description": s.description,
                    "paramCount": len(s.parameters),
                },
            }
        )

        # written_in edge
        lang_id = f"lang-{s.runtime}"
        runtimes_seen.add(s.runtime)
        graph_edges.append(
            {
                "id": f"written-{s.id}",
                "source": s.id,
                "target": lang_id,
                "type": "written_in",
            }
        )

        # labeled_as edges
        script_tags = get_script_tags(s.id)
        for t in script_tags:
            graph_edges.append(
                {
                    "id": f"labeled-{s.id}-{t.id}",
                    "source": s.id,
                    "target": f"tag-{t.id}",
                    "type": "labeled_as",
                }
            )

    # Language nodes
    for rt in runtimes_seen:
        nodes.append(
            {
                "id": f"lang-{rt}",
                "type": "language",
                "data": {"runtime": rt},
            }
        )

    # Tag nodes
    for t in tags:
        # Only include tags that are used by at least one script
        has_edge = any(e["target"] == f"tag-{t.id}" for e in graph_edges)
        if has_edge:
            nodes.append(
                {
                    "id": f"tag-{t.id}",
                    "type": "tag",
                    "data": {"name": t.name},
                }
            )

    # User-defined edges (from edges table)
    for e in edges:
        graph_edges.append(
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "type": e.relation,
                "data": {"metadata": e.metadata},
            }
        )

    return {"nodes": nodes, "edges": graph_edges}
