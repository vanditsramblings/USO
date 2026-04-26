"""Script management API routes."""

from fastapi import APIRouter, HTTPException, Query

from uso.db.connection import get_connection
from uso.detector import extract_header_meta
from uso.models import (
    ParameterCreate,
    ParameterOut,
    RunOut,
    ScriptCreate,
    ScriptMetricsOut,
    ScriptOut,
    ScriptUpdate,
)
from uso.services import script_service

router = APIRouter()


@router.get("", response_model=list[ScriptOut])
def list_scripts():
    return script_service.list_scripts()


@router.post("", response_model=ScriptOut, status_code=201)
def create_script(data: ScriptCreate):
    try:
        return script_service.register_script(data)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{script_id}", response_model=ScriptOut)
def get_script(script_id: str):
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.patch("/{script_id}", response_model=ScriptOut)
def update_script(script_id: str, data: ScriptUpdate):
    script = script_service.update_script(script_id, data)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.delete("/{script_id}", status_code=204)
def delete_script(script_id: str):
    if not script_service.delete_script(script_id):
        raise HTTPException(status_code=404, detail="Script not found")


@router.get("/{script_id}/meta")
def get_script_meta(script_id: str):
    """Return header-parsed metadata: icon, depends_on, tags."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return extract_header_meta(script.content)


@router.post("/{script_id}/parameters", response_model=ParameterOut, status_code=201)
def add_parameter(script_id: str, data: ParameterCreate):
    param = script_service.add_parameter(script_id, data)
    if not param:
        raise HTTPException(status_code=404, detail="Script not found")
    return param


@router.get("/{script_id}/runs", response_model=list[RunOut])
def get_script_runs(
    script_id: str,
    limit: int = Query(default=50, le=200),
    status: str | None = None,
):
    """List runs for a specific script with optional status filter."""
    if not script_service.get_script(script_id):
        raise HTTPException(status_code=404, detail="Script not found")
    conn = get_connection()
    sql = "SELECT * FROM runs WHERE script_id = ?"
    params: list = [script_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY start_time DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/{script_id}/metrics", response_model=ScriptMetricsOut)
def get_script_metrics(
    script_id: str,
    range: str = Query(default="7d", pattern=r"^(1d|7d|30d|all)$"),
):
    """Return aggregated execution metrics for a script."""
    if not script_service.get_script(script_id):
        raise HTTPException(status_code=404, detail="Script not found")

    days_map = {"1d": 1, "7d": 7, "30d": 30, "all": None}
    days = days_map[range]

    conn = get_connection()
    time_filter = ""
    time_params: list = [script_id]
    if days:
        time_filter = f" AND start_time >= datetime('now', '-{days} days')"

    base_sql = f"SELECT * FROM runs WHERE script_id = ?{time_filter}"
    rows = conn.execute(base_sql, time_params).fetchall()
    runs = [dict(r) for r in rows]

    total = len(runs)
    success_count = sum(1 for r in runs if r["status"] == "success")
    success_rate = success_count / total if total else 0.0

    runs_by_status: dict[str, int] = {}
    for r in runs:
        runs_by_status[r["status"]] = runs_by_status.get(r["status"], 0) + 1

    durations = [
        (r["start_time"], r["end_time"])
        for r in runs
        if r["start_time"] and r["end_time"]
    ]
    from datetime import datetime
    def _dur(s, e):
        fmt = "%Y-%m-%d %H:%M:%S"
        try:
            return (datetime.strptime(e, fmt) - datetime.strptime(s, fmt)).total_seconds()
        except Exception:
            return None

    dur_values = [d for d in (_dur(s, e) for s, e in durations) if d is not None]
    avg_duration_s = sum(dur_values) / len(dur_values) if dur_values else None

    recent_sql = (
        f"SELECT id, start_time, end_time, status FROM runs "
        f"WHERE script_id = ?{time_filter} AND start_time IS NOT NULL "
        f"ORDER BY start_time DESC LIMIT 20"
    )
    recent_rows = conn.execute(recent_sql, time_params).fetchall()
    recent_durations = [
        {
            "run_id": r["id"],
            "started_at": r["start_time"],
            "duration_s": _dur(r["start_time"], r["end_time"]) if r["end_time"] else None,
            "status": r["status"],
        }
        for r in recent_rows
    ]

    return ScriptMetricsOut(
        total_runs=total,
        success_rate=success_rate,
        avg_duration_s=avg_duration_s,
        runs_by_status=runs_by_status,
        recent_durations=recent_durations,
    )
