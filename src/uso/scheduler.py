"""APScheduler integration — BackgroundScheduler with DB-backed schedule metadata."""

import json
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from uso import db

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _build_trigger(trigger_type: str, trigger_args: dict):
    """Build an APScheduler trigger from type + kwargs."""
    match trigger_type:
        case "cron":
            return CronTrigger(**trigger_args)
        case "interval":
            return IntervalTrigger(**trigger_args)
        case "date":
            return DateTrigger(**trigger_args)
        case _:
            raise ValueError(f"Unknown trigger type: {trigger_type}")


def _execute_scheduled(script_id: str) -> None:
    """Job callback — execute a script via the run service."""
    from uso.services import run_service

    try:
        result = run_service.execute_script(script_id, trigger="scheduled")
        logger.info("Scheduled run %s for script %s: %s", result.id, script_id, result.status)
    except Exception:
        logger.exception("Scheduled execution failed for script %s", script_id)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def start() -> None:
    """Start the scheduler and load all enabled schedules from the DB."""
    sched = get_scheduler()
    if sched.running:
        return
    sched.start()
    _load_schedules()


def shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def _load_schedules() -> None:
    """Reconstruct APScheduler jobs from the schedules table."""
    sched = get_scheduler()
    for row in db.list_schedules():
        if not row["enabled"]:
            continue
        try:
            trigger_args = json.loads(row["trigger_args"])
            trigger = _build_trigger(row["trigger_type"], trigger_args)
            sched.add_job(
                _execute_scheduled,
                trigger=trigger,
                args=[row["script_id"]],
                id=row["id"],
                replace_existing=True,
                misfire_grace_time=row["misfire_grace_time"],
            )
        except Exception:
            logger.exception("Failed to load schedule %s", row["id"])


def add_job(
    schedule_id: str,
    script_id: str,
    trigger_type: str,
    trigger_args: dict,
    misfire_grace_time: int = 60,
) -> None:
    """Register a new job with the running scheduler."""
    sched = get_scheduler()
    trigger = _build_trigger(trigger_type, trigger_args)
    sched.add_job(
        _execute_scheduled,
        trigger=trigger,
        args=[script_id],
        id=schedule_id,
        replace_existing=True,
        misfire_grace_time=misfire_grace_time,
    )


def remove_job(schedule_id: str) -> None:
    sched = get_scheduler()
    try:
        sched.remove_job(schedule_id)
    except Exception:
        pass  # Job may not exist in scheduler


def pause_job(schedule_id: str) -> None:
    sched = get_scheduler()
    try:
        sched.pause_job(schedule_id)
    except Exception:
        pass


def resume_job(schedule_id: str, schedule_row: dict) -> None:
    """Resume or re-add a paused job."""
    sched = get_scheduler()
    try:
        sched.resume_job(schedule_id)
    except Exception:
        trigger_args = json.loads(schedule_row["trigger_args"])
        add_job(
            schedule_id,
            schedule_row["script_id"],
            schedule_row["trigger_type"],
            trigger_args,
            schedule_row["misfire_grace_time"],
        )


def get_next_run_time(schedule_id: str) -> str | None:
    sched = get_scheduler()
    if not sched.running:
        return None
    job = sched.get_job(schedule_id)
    nrt = getattr(job, "next_run_time", None) if job else None
    return nrt.isoformat() if nrt else None
