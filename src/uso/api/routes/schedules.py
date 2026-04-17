"""Schedule management API routes."""

from fastapi import APIRouter, HTTPException

from uso.models import ScheduleCreate, ScheduleOut
from uso.services import schedule_service

router = APIRouter()


@router.get("", response_model=list[ScheduleOut])
def list_schedules(script_id: str | None = None):
    return schedule_service.list_schedules(script_id=script_id)


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(data: ScheduleCreate):
    try:
        return schedule_service.create_schedule(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(schedule_id: str):
    sched = schedule_service.get_schedule(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.patch("/{schedule_id}/toggle", response_model=ScheduleOut)
def toggle_schedule(schedule_id: str, enabled: bool = True):
    sched = schedule_service.toggle_schedule(schedule_id, enabled)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return sched


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str):
    if not schedule_service.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
