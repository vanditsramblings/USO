"""Script management API routes."""

from fastapi import APIRouter, HTTPException

from uso.models import ParameterCreate, ParameterOut, ScriptCreate, ScriptOut, ScriptUpdate
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


@router.post("/{script_id}/parameters", response_model=ParameterOut, status_code=201)
def add_parameter(script_id: str, data: ParameterCreate):
    param = script_service.add_parameter(script_id, data)
    if not param:
        raise HTTPException(status_code=404, detail="Script not found")
    return param
