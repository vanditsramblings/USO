"""Tests for uso.services.script_service."""

import pytest

from uso.db import init_db
from uso.models import ParameterCreate, ScriptCreate, ScriptUpdate
from uso.services import script_service


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)


def test_register_script_with_params():
    data = ScriptCreate(
        name="test-script",
        runtime="py",
        content="print('hi')",
        description="A test",
        parameters=[
            ParameterCreate(key="API_KEY", is_secret=True),
            ParameterCreate(key="LOG_LEVEL"),
        ],
    )
    script = script_service.register_script(data)
    assert script.name == "test-script"
    assert script.runtime == "py"
    assert len(script.parameters) == 2
    assert script.parameters[0].key == "API_KEY"
    assert script.parameters[0].is_secret is True


def test_list_scripts_empty():
    assert script_service.list_scripts() == []


def test_list_scripts():
    script_service.register_script(ScriptCreate(name="a", runtime="sh", content="echo a"))
    script_service.register_script(ScriptCreate(name="b", runtime="py", content="pass"))
    scripts = script_service.list_scripts()
    assert len(scripts) == 2


def test_get_script_by_name():
    script_service.register_script(ScriptCreate(name="finder", runtime="py", content="import os"))
    script = script_service.get_script_by_name("finder")
    assert script is not None
    assert script.name == "finder"


def test_update_script():
    script = script_service.register_script(
        ScriptCreate(name="updater", runtime="js", content="console.log(1)")
    )
    updated = script_service.update_script(
        script.id, ScriptUpdate(content="console.log(2)", description="v2")
    )
    assert updated.version == 2
    assert updated.content == "console.log(2)"
    assert updated.description == "v2"


def test_delete_script():
    script = script_service.register_script(
        ScriptCreate(name="deleteme", runtime="sh", content="echo bye")
    )
    assert script_service.delete_script(script.id) is True
    assert script_service.get_script(script.id) is None


def test_delete_nonexistent():
    assert script_service.delete_script("nonexistent-id") is False
