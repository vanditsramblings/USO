"""Comprehensive metrics endpoint."""

import time
from pathlib import Path

import psutil
from fastapi import APIRouter

from uso.db.connection import DEFAULT_DB_PATH, get_connection

router = APIRouter()

_START_TIME = time.time()


@router.get("/api/metrics")
def get_metrics() -> dict:
    """Return detailed runtime, DB, and execution statistics."""
    with get_connection() as conn:
        scripts_total = conn.execute("SELECT COUNT(*) FROM scripts").fetchone()[0]
        scripts_by_runtime = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT runtime, COUNT(*) FROM scripts GROUP BY runtime"
            ).fetchall()
        }
        runs_total = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        runs_by_status = {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT status, COUNT(*) FROM runs GROUP BY status"
            ).fetchall()
        }
        avg_duration = conn.execute(
            """SELECT AVG(
                (julianday(end_time) - julianday(start_time)) * 86400
               )
               FROM runs WHERE end_time IS NOT NULL AND start_time IS NOT NULL"""
        ).fetchone()[0]
        schedules_total = conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
        schedules_enabled = conn.execute(
            "SELECT COUNT(*) FROM schedules WHERE enabled = 1"
        ).fetchone()[0]
        tags_total = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
        edges_total = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        workflows_total = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
        recent_failures = conn.execute(
            """SELECT s.name, r.end_time FROM runs r
               JOIN scripts s ON s.id = r.script_id
               WHERE r.status = 'failure'
               ORDER BY r.end_time DESC LIMIT 5"""
        ).fetchall()

    db_path = Path(DEFAULT_DB_PATH)
    db_size = db_path.stat().st_size if db_path.exists() else 0

    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(".")

    return {
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "scripts": {
            "total": scripts_total,
            "by_runtime": scripts_by_runtime,
        },
        "runs": {
            "total": runs_total,
            "by_status": runs_by_status,
            "avg_duration_seconds": round(avg_duration, 3) if avg_duration else None,
            "recent_failures": [
                {"script": r[0], "ended_at": r[1]} for r in recent_failures
            ],
        },
        "schedules": {
            "total": schedules_total,
            "enabled": schedules_enabled,
        },
        "knowledge_graph": {
            "tags": tags_total,
            "edges": edges_total,
            "workflows": workflows_total,
        },
        "storage": {
            "db_size_bytes": db_size,
            "disk_total_gb": round(disk.total / 1024**3, 2),
            "disk_used_gb": round(disk.used / 1024**3, 2),
            "disk_free_gb": round(disk.free / 1024**3, 2),
            "disk_percent": disk.percent,
        },
        "memory": {
            "total_mb": round(vm.total / 1024 / 1024, 1),
            "used_mb": round(vm.used / 1024 / 1024, 1),
            "percent": vm.percent,
        },
    }
