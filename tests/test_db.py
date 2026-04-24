"""Tests for uso.db module — UUID-based schema."""

import sqlite3

import pytest

from uso.db import (
    add_parameter,
    create_run,
    create_script,
    delete_script,
    get_connection,
    get_parameters,
    get_runs,
    get_script,
    get_script_by_name,
    init_db,
    list_scripts,
    update_run,
    update_script,
)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Use a temp database for each test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)


def test_wal_mode_enabled():
    conn = get_connection()
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert mode == "wal"


def test_create_returns_uuid():
    sid = create_script("hello", "sh", "echo hello", "A greeting script")
    assert isinstance(sid, str)
    assert len(sid) == 36 and sid.count("-") == 4


def test_create_and_get_script():
    sid = create_script("hello", "sh", "echo hello", "A greeting script")
    script = get_script(sid)
    assert script["name"] == "hello"
    assert script["runtime"] == "sh"
    assert script["content"] == "echo hello"
    assert script["version"] == 1


def test_get_script_by_name():
    create_script("finder", "py", "import os")
    script = get_script_by_name("finder")
    assert script is not None
    assert script["name"] == "finder"


def test_list_scripts():
    create_script("a", "sh", "echo a")
    create_script("b", "py", "print('b')")
    scripts = list_scripts()
    assert len(scripts) == 2
    assert scripts[0]["name"] == "a"


def test_update_script_bumps_version():
    sid = create_script("updater", "js", "console.log(1)")
    update_script(sid, "console.log(2)", "Updated")
    script = get_script(sid)
    assert script["version"] == 2
    assert script["content"] == "console.log(2)"
    assert script["description"] == "Updated"


def test_delete_script():
    sid = create_script("deleteme", "sh", "echo bye")
    delete_script(sid)
    assert get_script(sid) is None


def test_unique_name_constraint():
    create_script("unique", "sh", "echo 1")
    with pytest.raises(sqlite3.IntegrityError):
        create_script("unique", "sh", "echo 2")


def test_invalid_runtime():
    with pytest.raises(sqlite3.IntegrityError):
        create_script("bad", "rb", "puts 'hi'")


def test_parameters_crud():
    sid = create_script("paramtest", "py", "pass")
    add_parameter(sid, "API_KEY", is_secret=True)
    add_parameter(sid, "LOG_LEVEL", is_secret=False)
    params = get_parameters(sid)
    assert len(params) == 2
    secrets = [p for p in params if p["is_secret"]]
    assert len(secrets) == 1
    assert secrets[0]["key"] == "API_KEY"
    assert len(params[0]["id"]) == 36


def test_runs_crud():
    sid = create_script("runner", "sh", "echo run")
    rid = create_run(sid)
    assert len(rid) == 36
    update_run(rid, status="success", exit_code=0, logs="done\n")
    runs = get_runs(script_id=sid)
    assert len(runs) == 1
    assert runs[0]["status"] == "success"
    assert runs[0]["exit_code"] == 0


def test_cascade_delete():
    sid = create_script("cascade", "sh", "echo x")
    add_parameter(sid, "KEY")
    create_run(sid)
    delete_script(sid)
    assert get_parameters(sid) == []
    assert get_runs(script_id=sid) == []
