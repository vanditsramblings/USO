"""Tests for schedule service and scheduler module."""

import json

import pytest

from uso import scheduler
from uso.db import create_script, get_schedule, init_db, list_schedules
from uso.models import ScheduleCreate
from uso.services import schedule_service


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("uso.db.connection.DEFAULT_DB_PATH", db_path)
    import uso.db as db_mod

    if hasattr(db_mod._local, "connections"):
        db_mod._local.connections.clear()
    init_db(db_path)
    scheduler.shutdown()
    scheduler.start()
    yield
    scheduler.shutdown()


@pytest.fixture()
def script_id():
    return create_script("test-cron", "sh", "echo scheduled", "A cron test")


def test_create_schedule(script_id):
    data = ScheduleCreate(
        script_id=script_id,
        trigger_type="interval",
        trigger_args={"minutes": 30},
    )
    sched = schedule_service.create_schedule(data)
    assert sched.id
    assert sched.trigger_type == "interval"
    assert sched.trigger_args == {"minutes": 30}
    assert sched.enabled is True


def test_create_schedule_missing_script():
    data = ScheduleCreate(
        script_id="nonexistent",
        trigger_type="cron",
        trigger_args={"minute": "0", "hour": "6"},
    )
    with pytest.raises(ValueError, match="Script not found"):
        schedule_service.create_schedule(data)


def test_list_schedules(script_id):
    schedule_service.create_schedule(
        ScheduleCreate(script_id=script_id, trigger_type="interval", trigger_args={"minutes": 10})
    )
    schedule_service.create_schedule(
        ScheduleCreate(script_id=script_id, trigger_type="cron", trigger_args={"minute": "*/5"})
    )
    result = schedule_service.list_schedules()
    assert len(result) == 2


def test_toggle_schedule(script_id):
    sched = schedule_service.create_schedule(
        ScheduleCreate(script_id=script_id, trigger_type="interval", trigger_args={"minutes": 15})
    )
    toggled = schedule_service.toggle_schedule(sched.id, enabled=False)
    assert toggled.enabled is False

    toggled = schedule_service.toggle_schedule(sched.id, enabled=True)
    assert toggled.enabled is True


def test_delete_schedule(script_id):
    sched = schedule_service.create_schedule(
        ScheduleCreate(script_id=script_id, trigger_type="interval", trigger_args={"minutes": 5})
    )
    assert schedule_service.delete_schedule(sched.id) is True
    assert get_schedule(sched.id) is None
    assert schedule_service.delete_schedule(sched.id) is False


def test_cron_trigger(script_id):
    data = ScheduleCreate(
        script_id=script_id,
        trigger_type="cron",
        trigger_args={"hour": "6", "minute": "30", "day_of_week": "mon-fri"},
    )
    sched = schedule_service.create_schedule(data)
    assert sched.next_run_time is not None


def test_schedule_persisted_in_db(script_id):
    schedule_service.create_schedule(
        ScheduleCreate(script_id=script_id, trigger_type="interval", trigger_args={"seconds": 60})
    )
    rows = list_schedules()
    assert len(rows) == 1
    assert json.loads(rows[0]["trigger_args"]) == {"seconds": 60}
