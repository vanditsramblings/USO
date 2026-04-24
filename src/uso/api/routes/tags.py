"""Tag management API routes."""

from fastapi import APIRouter, HTTPException

from uso.models import TagCreate, TagOut
from uso.services import tag_service

router = APIRouter()


@router.get("", response_model=list[TagOut])
def list_tags():
    return tag_service.list_tags()


@router.post("", response_model=TagOut, status_code=201)
def create_tag(data: TagCreate):
    try:
        return tag_service.create_tag(data)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: str):
    if not tag_service.delete_tag(tag_id):
        raise HTTPException(status_code=404, detail="Tag not found")


@router.get("/script/{script_id}", response_model=list[TagOut])
def get_script_tags(script_id: str):
    return tag_service.get_script_tags(script_id)


@router.post("/script/{script_id}/{tag_id}", status_code=204)
def tag_script(script_id: str, tag_id: str):
    tag_service.tag_script(script_id, tag_id)


@router.delete("/script/{script_id}/{tag_id}", status_code=204)
def untag_script(script_id: str, tag_id: str):
    tag_service.untag_script(script_id, tag_id)
