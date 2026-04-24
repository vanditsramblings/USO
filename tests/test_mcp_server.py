"""Tests for uso.mcp_server module."""

import pytest

from uso.db import create_script, init_db
from uso.mcp_server import get_run, get_script, list_scripts, run_script


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)


@pytest.fixture()
def script_id():
    return create_script("mcp-test", "sh", "echo mcp-hello", "MCP test script")


def test_list_scripts(script_id):
    result = list_scripts()
    assert len(result) == 1
    assert result[0]["name"] == "mcp-test"
    assert result[0]["id"] == script_id


def test_get_script(script_id):
    result = get_script(script_id)
    assert result["name"] == "mcp-test"
    assert result["runtime"] == "sh"


def test_get_script_not_found():
    assert get_script("nonexistent") is None


def test_run_script(script_id):
    result = run_script(script_id, timeout=10)
    assert result["status"] == "success"
    assert "mcp-hello" in result["logs"]


def test_get_run(script_id):
    result = run_script(script_id, timeout=10)
    run = get_run(result["run_id"])
    assert run["status"] == "success"


def test_get_run_not_found():
    assert get_run("nonexistent") is None
