"""Knowledge graph edge API routes."""

from fastapi import APIRouter, HTTPException

from uso.models import EdgeCreate, EdgeOut
from uso.services import edge_service

router = APIRouter()


@router.get("", response_model=list[EdgeOut])
def list_edges(script_id: str | None = None):
    return edge_service.list_edges(script_id)


@router.post("", response_model=EdgeOut, status_code=201)
def create_edge(data: EdgeCreate):
    try:
        return edge_service.create_edge(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{edge_id}", response_model=EdgeOut)
def get_edge(edge_id: str):
    edge = edge_service.get_edge(edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    return edge


@router.delete("/{edge_id}", status_code=204)
def delete_edge(edge_id: str):
    if not edge_service.delete_edge(edge_id):
        raise HTTPException(status_code=404, detail="Edge not found")
