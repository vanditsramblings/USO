"""Tests for tag, edge, and workflow API routes."""

import pytest
from fastapi.testclient import TestClient

from uso.api.app import create_app
from uso.db import init_db


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)
    from uso import scheduler

    scheduler.shutdown()


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _create_script(client, name="test-script", runtime="sh", content="echo hello"):
    resp = client.post(
        "/api/scripts", json={"name": name, "runtime": runtime, "content": content}
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# --- Tags ---


def test_create_tag(client):
    resp = client.post("/api/tags", json={"name": "ETL"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "ETL"


def test_list_tags(client):
    baseline = len(client.get("/api/tags").json())
    client.post("/api/tags", json={"name": "ETL"})
    client.post("/api/tags", json={"name": "DevOps"})
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    assert len(resp.json()) == baseline + 2


def test_delete_tag(client):
    baseline = len(client.get("/api/tags").json())
    tag = client.post("/api/tags", json={"name": "tmp"}).json()
    resp = client.delete(f"/api/tags/{tag['id']}")
    assert resp.status_code == 204
    assert len(client.get("/api/tags").json()) == baseline


def test_tag_script(client):
    sid = _create_script(client)
    tag = client.post("/api/tags", json={"name": "ETL"}).json()
    resp = client.post(f"/api/tags/script/{sid}/{tag['id']}")
    assert resp.status_code == 204
    tags = client.get(f"/api/tags/script/{sid}").json()
    assert len(tags) == 1
    assert tags[0]["name"] == "ETL"


def test_untag_script(client):
    sid = _create_script(client)
    tag = client.post("/api/tags", json={"name": "tmp"}).json()
    client.post(f"/api/tags/script/{sid}/{tag['id']}")
    client.delete(f"/api/tags/script/{sid}/{tag['id']}")
    tags = client.get(f"/api/tags/script/{sid}").json()
    assert len(tags) == 0


# --- Edges ---


def test_create_edge(client):
    s1 = _create_script(client, "script-a")
    s2 = _create_script(client, "script-b")
    resp = client.post(
        "/api/edges",
        json={"source_id": s1, "target_id": s2, "relation": "data_flow"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == s1
    assert data["relation"] == "data_flow"


def test_list_edges_filter(client):
    s1 = _create_script(client, "script-a")
    s2 = _create_script(client, "script-b")
    s3 = _create_script(client, "script-c")
    client.post("/api/edges", json={"source_id": s1, "target_id": s2, "relation": "manual"})
    client.post("/api/edges", json={"source_id": s2, "target_id": s3, "relation": "sequential"})
    # All edges
    assert len(client.get("/api/edges").json()) == 2
    # Filtered to s1 (source or target)
    assert len(client.get(f"/api/edges?script_id={s1}").json()) == 1


def test_self_edge_rejected(client):
    s1 = _create_script(client)
    resp = client.post(
        "/api/edges", json={"source_id": s1, "target_id": s1, "relation": "manual"}
    )
    assert resp.status_code == 400


def test_delete_edge(client):
    s1 = _create_script(client, "a")
    s2 = _create_script(client, "b")
    edge = client.post(
        "/api/edges", json={"source_id": s1, "target_id": s2, "relation": "manual"}
    ).json()
    resp = client.delete(f"/api/edges/{edge['id']}")
    assert resp.status_code == 204


# --- Workflows ---


def test_create_workflow(client):
    resp = client.post(
        "/api/workflows",
        json={"name": "etl-pipeline", "description": "Extract-Transform-Load"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "etl-pipeline"


def test_create_workflow_with_nodes(client):
    s1 = _create_script(client, "extract")
    s2 = _create_script(client, "transform")
    resp = client.post(
        "/api/workflows",
        json={
            "name": "pipeline",
            "nodes": [
                {"script_id": s1, "position_x": 0, "position_y": 0},
                {"script_id": s2, "position_x": 200, "position_y": 0},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["nodes"]) == 2


def test_add_node_to_workflow(client):
    sid = _create_script(client)
    wf = client.post("/api/workflows", json={"name": "wf"}).json()
    resp = client.post(
        f"/api/workflows/{wf['id']}/nodes",
        json={"script_id": sid, "position_x": 100, "position_y": 50},
    )
    assert resp.status_code == 201
    assert resp.json()["script_id"] == sid


def test_add_edge_to_workflow(client):
    s1 = _create_script(client, "a")
    s2 = _create_script(client, "b")
    wf = client.post(
        "/api/workflows",
        json={
            "name": "wf",
            "nodes": [{"script_id": s1}, {"script_id": s2}],
        },
    ).json()
    n1, n2 = wf["nodes"][0]["id"], wf["nodes"][1]["id"]
    resp = client.post(
        f"/api/workflows/{wf['id']}/edges",
        json={
            "source_node_id": n1,
            "target_node_id": n2,
            "condition": {"type": "status", "value": "success"},
        },
    )
    assert resp.status_code == 201


def test_delete_workflow(client):
    wf = client.post("/api/workflows", json={"name": "tmp"}).json()
    resp = client.delete(f"/api/workflows/{wf['id']}")
    assert resp.status_code == 204


def test_delete_workflow_node(client):
    sid = _create_script(client)
    wf = client.post("/api/workflows", json={"name": "wf"}).json()
    node = client.post(
        f"/api/workflows/{wf['id']}/nodes",
        json={"script_id": sid, "position_x": 0, "position_y": 0},
    ).json()
    resp = client.delete(f"/api/workflows/{wf['id']}/nodes/{node['id']}")
    assert resp.status_code == 204
    # Verify the workflow now has no nodes
    fresh = client.get(f"/api/workflows/{wf['id']}").json()
    assert len(fresh["nodes"]) == 0


def test_delete_workflow_node_not_found(client):
    wf = client.post("/api/workflows", json={"name": "wf2"}).json()
    resp = client.delete(f"/api/workflows/{wf['id']}/nodes/nonexistent")
    assert resp.status_code == 404


def test_update_workflow_node_position(client):
    sid = _create_script(client)
    wf = client.post("/api/workflows", json={"name": "wf"}).json()
    node = client.post(
        f"/api/workflows/{wf['id']}/nodes",
        json={"script_id": sid, "position_x": 0, "position_y": 0},
    ).json()
    resp = client.patch(
        f"/api/workflows/{wf['id']}/nodes/{node['id']}",
        json={"position_x": 350, "position_y": 200},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["position_x"] == 350
    assert data["position_y"] == 200


def test_update_workflow_node_config(client):
    sid = _create_script(client)
    wf = client.post("/api/workflows", json={"name": "wf"}).json()
    node = client.post(
        f"/api/workflows/{wf['id']}/nodes",
        json={"script_id": sid},
    ).json()
    resp = client.patch(
        f"/api/workflows/{wf['id']}/nodes/{node['id']}",
        json={"config": {"DB_HOST": "localhost", "PORT": "5432"}},
    )
    assert resp.status_code == 200
    assert resp.json()["config"] == {"DB_HOST": "localhost", "PORT": "5432"}


def test_delete_workflow_edge(client):
    s1 = _create_script(client, "aa")
    s2 = _create_script(client, "bb")
    wf = client.post(
        "/api/workflows",
        json={"name": "wf", "nodes": [{"script_id": s1}, {"script_id": s2}]},
    ).json()
    n1, n2 = wf["nodes"][0]["id"], wf["nodes"][1]["id"]
    edge = client.post(
        f"/api/workflows/{wf['id']}/edges",
        json={"source_node_id": n1, "target_node_id": n2},
    ).json()
    resp = client.delete(f"/api/workflows/{wf['id']}/edges/{edge['id']}")
    assert resp.status_code == 204
    fresh = client.get(f"/api/workflows/{wf['id']}").json()
    assert len(fresh["edges"]) == 0


def test_delete_workflow_edge_not_found(client):
    wf = client.post("/api/workflows", json={"name": "wf3"}).json()
    resp = client.delete(f"/api/workflows/{wf['id']}/edges/nonexistent")
    assert resp.status_code == 404


def test_detect_endpoint(client):
    resp = client.post(
        "/api/detect",
        json={
            "content": '"""Hello world."""\nimport os\nurl = os.getenv("API_URL")\n',
            "runtime": "py",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Hello world."
    assert any(p["key"] == "API_URL" for p in data["parameters"])
