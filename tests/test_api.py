"""Tests for USO FastAPI endpoints."""

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


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_script(client):
    resp = client.post(
        "/api/scripts",
        json={
            "name": "test-script",
            "runtime": "sh",
            "content": "echo hello",
            "description": "A test",
            "parameters": [{"key": "API_KEY", "is_secret": True}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-script"
    assert len(data["id"]) == 36
    assert len(data["parameters"]) == 1


def test_list_scripts(client):
    before = len(client.get("/api/scripts").json())
    client.post(
        "/api/scripts",
        json={"name": "a", "runtime": "sh", "content": "echo a"},
    )
    client.post(
        "/api/scripts",
        json={"name": "b", "runtime": "py", "content": "pass"},
    )
    resp = client.get("/api/scripts")
    assert resp.status_code == 200
    assert len(resp.json()) == before + 2


def test_get_script(client):
    create = client.post(
        "/api/scripts",
        json={"name": "getter", "runtime": "py", "content": "print(1)"},
    )
    sid = create.json()["id"]
    resp = client.get(f"/api/scripts/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "getter"


def test_get_script_not_found(client):
    resp = client.get("/api/scripts/nonexistent")
    assert resp.status_code == 404


def test_update_script(client):
    create = client.post(
        "/api/scripts",
        json={"name": "updater", "runtime": "js", "content": "console.log(1)"},
    )
    sid = create.json()["id"]
    resp = client.patch(
        f"/api/scripts/{sid}",
        json={"content": "console.log(2)", "description": "v2"},
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


def test_delete_script(client):
    create = client.post(
        "/api/scripts",
        json={"name": "deleteme", "runtime": "sh", "content": "echo bye"},
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/scripts/{sid}")
    assert resp.status_code == 204
    assert client.get(f"/api/scripts/{sid}").status_code == 404


def test_create_run(client):
    create = client.post(
        "/api/scripts",
        json={"name": "runner", "runtime": "sh", "content": "echo 'ran ok'"},
    )
    sid = create.json()["id"]
    resp = client.post(
        "/api/runs",
        json={"script_id": sid, "timeout": 10},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


def test_list_runs(client):
    create = client.post(
        "/api/scripts",
        json={"name": "multi", "runtime": "sh", "content": "echo ok"},
    )
    sid = create.json()["id"]
    client.post("/api/runs", json={"script_id": sid, "timeout": 10})
    client.post("/api/runs", json={"script_id": sid, "timeout": 10})
    resp = client.get("/api/runs", params={"script_id": sid})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_add_parameter(client):
    create = client.post(
        "/api/scripts",
        json={"name": "paramtest", "runtime": "py", "content": "pass"},
    )
    sid = create.json()["id"]
    resp = client.post(
        f"/api/scripts/{sid}/parameters",
        json={"key": "NEW_KEY", "is_secret": False},
    )
    assert resp.status_code == 201
    assert resp.json()["key"] == "NEW_KEY"


# --- Schedule API ---


def test_create_schedule(client):
    script = client.post(
        "/api/scripts",
        json={"name": "sched-test", "runtime": "sh", "content": "echo hi"},
    )
    sid = script.json()["id"]
    resp = client.post(
        "/api/schedules",
        json={
            "script_id": sid,
            "trigger_type": "interval",
            "trigger_args": {"minutes": 10},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["trigger_type"] == "interval"
    assert data["enabled"] is True


def test_list_schedules(client):
    script = client.post(
        "/api/scripts",
        json={"name": "sched-list", "runtime": "sh", "content": "echo list"},
    )
    sid = script.json()["id"]
    client.post(
        "/api/schedules",
        json={"script_id": sid, "trigger_type": "interval", "trigger_args": {"seconds": 30}},
    )
    resp = client.get("/api/schedules")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_toggle_schedule(client):
    script = client.post(
        "/api/scripts",
        json={"name": "sched-toggle", "runtime": "sh", "content": "echo toggle"},
    )
    sid = script.json()["id"]
    sched = client.post(
        "/api/schedules",
        json={"script_id": sid, "trigger_type": "interval", "trigger_args": {"minutes": 5}},
    ).json()
    resp = client.patch(f"/api/schedules/{sched['id']}/toggle?enabled=false")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_delete_schedule(client):
    script = client.post(
        "/api/scripts",
        json={"name": "sched-del", "runtime": "sh", "content": "echo del"},
    )
    sid = script.json()["id"]
    sched = client.post(
        "/api/schedules",
        json={"script_id": sid, "trigger_type": "interval", "trigger_args": {"minutes": 1}},
    ).json()
    resp = client.delete(f"/api/schedules/{sched['id']}")
    assert resp.status_code == 204
