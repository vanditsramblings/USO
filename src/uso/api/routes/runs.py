"""Run management API routes."""

from fastapi import APIRouter, HTTPException

from uso.models import RunCreate, RunOut
from uso.services import run_service

router = APIRouter()


@router.get("", response_model=list[RunOut])
def list_runs(script_id: str | None = None, limit: int = 50):
    return run_service.list_runs(script_id=script_id, limit=limit)


@router.post("", response_model=RunOut, status_code=201)
def create_run(data: RunCreate):
    try:
        return run_service.execute_script(
            script_id=data.script_id,
            env=data.env or None,
            timeout=data.timeout,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: str):
    run = run_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
