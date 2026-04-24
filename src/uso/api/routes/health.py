"""Health check endpoint — comprehensive system + dependency status."""

import platform
import sys
import time
from pathlib import Path

import psutil
from fastapi import APIRouter

from uso import __version__
from uso.db.connection import DEFAULT_DB_PATH, get_connection

router = APIRouter()

_START_TIME = time.time()


@router.get("/health")
def health_check() -> dict:
    """Return comprehensive health status including system, DB, and process info."""
    db_status = "ok"
    db_details: dict = {}
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM scripts")
            db_details["scripts"] = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(*) FROM runs")
            db_details["runs"] = cur.fetchone()[0]
            db_details["wal_enabled"] = True
    except Exception as exc:
        db_status = f"error: {exc}"

    db_path = Path(DEFAULT_DB_PATH)
    db_size_bytes = db_path.stat().st_size if db_path.exists() else 0

    proc = psutil.Process()
    mem = proc.memory_info()
    cpu_pct = psutil.cpu_percent(interval=None)
    vm = psutil.virtual_memory()

    return {
        "status": db_status if db_status == "ok" else "degraded",
        "version": __version__,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "python": sys.version,
        "platform": platform.platform(),
        "process": {
            "pid": proc.pid,
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
            "cpu_percent": cpu_pct,
        },
        "system": {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": cpu_pct,
            "memory_total_mb": round(vm.total / 1024 / 1024, 1),
            "memory_used_mb": round(vm.used / 1024 / 1024, 1),
            "memory_percent": vm.percent,
        },
        "database": {
            "status": db_status,
            "path": str(db_path),
            "size_bytes": db_size_bytes,
            **db_details,
        },
    }
