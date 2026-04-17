"""Schedule service — business logic for schedule CRUD and scheduler sync."""

import json

from uso import db, scheduler
from uso.models import ScheduleCreate, ScheduleOut


def create_schedule(data: ScheduleCreate) -> ScheduleOut:
    script = db.get_script(data.script_id)
    if not script:
        raise ValueError(f"Script not found: {data.script_id}")

    trigger_args_json = json.dumps(data.trigger_args)
    schedule_id = db.create_schedule(
        script_id=data.script_id,
        trigger_type=data.trigger_type.value,
        trigger_args=trigger_args_json,
        misfire_grace_time=data.misfire_grace_time,
    )
    scheduler.add_job(
        schedule_id,
        data.script_id,
        data.trigger_type.value,
        data.trigger_args,
        data.misfire_grace_time,
    )
    return get_schedule(schedule_id)


def get_schedule(schedule_id: str) -> ScheduleOut | None:
    row = db.get_schedule(schedule_id)
    if not row:
        return None
    return _row_to_out(row)


def list_schedules(script_id: str | None = None) -> list[ScheduleOut]:
    rows = db.list_schedules(script_id=script_id)
    return [_row_to_out(r) for r in rows]


def toggle_schedule(schedule_id: str, enabled: bool) -> ScheduleOut | None:
    row = db.get_schedule(schedule_id)
    if not row:
        return None
    db.update_schedule_enabled(schedule_id, enabled)
    if enabled:
        scheduler.resume_job(schedule_id, row)
    else:
        scheduler.pause_job(schedule_id)
    return get_schedule(schedule_id)


def delete_schedule(schedule_id: str) -> bool:
    row = db.get_schedule(schedule_id)
    if not row:
        return False
    scheduler.remove_job(schedule_id)
    db.delete_schedule(schedule_id)
    return True


def _row_to_out(row: dict) -> ScheduleOut:
    return ScheduleOut(
        id=row["id"],
        script_id=row["script_id"],
        trigger_type=row["trigger_type"],
        trigger_args=json.loads(row["trigger_args"]),
        enabled=bool(row["enabled"]),
        misfire_grace_time=row["misfire_grace_time"],
        next_run_time=scheduler.get_next_run_time(row["id"]),
        created_at=row["created_at"],
    )
