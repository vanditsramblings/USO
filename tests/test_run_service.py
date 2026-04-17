"""Tests for uso.services.run_service."""

import pytest

from uso.db import init_db
from uso.models import ScriptCreate
from uso.services import run_service, script_service


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)


@pytest.fixture()
def sample_script():
    return script_service.register_script(
        ScriptCreate(name="echo-test", runtime="sh", content="echo 'run ok'")
    )


def test_execute_script(sample_script):
    run = run_service.execute_script(sample_script.id, timeout=10)
    assert run.status == "success"
    assert run.exit_code == 0


def test_execute_failing_script():
    script = script_service.register_script(
        ScriptCreate(name="fail-test", runtime="sh", content="exit 42")
    )
    run = run_service.execute_script(script.id, timeout=10)
    assert run.status == "failure"
    assert run.exit_code == 42


def test_execute_nonexistent():
    with pytest.raises(ValueError, match="Script not found"):
        run_service.execute_script("does-not-exist")


def test_list_runs(sample_script):
    run_service.execute_script(sample_script.id, timeout=10)
    run_service.execute_script(sample_script.id, timeout=10)
    runs = run_service.list_runs(script_id=sample_script.id)
    assert len(runs) == 2


def test_execute_with_env():
    script = script_service.register_script(
        ScriptCreate(
            name="env-test",
            runtime="py",
            content="import os; print(os.environ.get('MY_VAR', 'missing'))",
        )
    )
    run = run_service.execute_script(script.id, env={"MY_VAR": "hello"}, timeout=10)
    assert run.status == "success"
