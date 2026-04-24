"""Workflow (DAG) management API routes."""

import asyncio
import json
import threading

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from uso.models import (
    WorkflowCreate,
    WorkflowEdgeCreate,
    WorkflowEdgeOut,
    WorkflowNodeCreate,
    WorkflowNodeOut,
    WorkflowNodeUpdate,
    WorkflowOut,
    WorkflowRunOut,
)
from uso.services import workflow_service

router = APIRouter()


@router.get("", response_model=list[WorkflowOut])
def list_workflows():
    return workflow_service.list_workflows()


@router.post("", response_model=WorkflowOut, status_code=201)
def create_workflow(data: WorkflowCreate):
    try:
        return workflow_service.create_workflow(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: str):
    wf = workflow_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: str):
    if not workflow_service.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/{workflow_id}/nodes", response_model=WorkflowNodeOut, status_code=201)
def add_node(workflow_id: str, data: WorkflowNodeCreate):
    try:
        node = workflow_service.add_node(
            workflow_id, data.script_id, data.position_x, data.position_y, data.config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not node:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return node


@router.patch("/{workflow_id}/nodes/{node_id}", response_model=WorkflowNodeOut)
def update_node(workflow_id: str, node_id: str, data: WorkflowNodeUpdate):
    node = workflow_service.update_node(
        workflow_id, node_id, data.position_x, data.position_y, data.config
    )
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.delete("/{workflow_id}/nodes/{node_id}", status_code=204)
def delete_node(workflow_id: str, node_id: str):
    if not workflow_service.delete_node(workflow_id, node_id):
        raise HTTPException(status_code=404, detail="Node not found")


@router.post("/{workflow_id}/edges", response_model=WorkflowEdgeOut, status_code=201)
def add_edge(workflow_id: str, data: WorkflowEdgeCreate):
    edge = workflow_service.add_edge(
        workflow_id, data.source_node_id, data.target_node_id, data.condition
    )
    if not edge:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return edge


@router.delete("/{workflow_id}/edges/{edge_id}", status_code=204)
def delete_edge(workflow_id: str, edge_id: str):
    if not workflow_service.delete_edge(workflow_id, edge_id):
        raise HTTPException(status_code=404, detail="Edge not found")


@router.post("/{workflow_id}/execute", response_model=WorkflowRunOut, status_code=201)
def execute_workflow(workflow_id: str, env: dict[str, str] | None = None, timeout: int = 60):
    try:
        return workflow_service.execute_workflow(workflow_id, env=env, timeout=timeout)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunOut])
def list_runs(workflow_id: str):
    return workflow_service.list_workflow_runs(workflow_id)


@router.websocket("/{workflow_id}/ws")
async def workflow_ws(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    loop = asyncio.get_event_loop()
    events: asyncio.Queue = asyncio.Queue()

    def on_event(evt):
        loop.call_soon_threadsafe(events.put_nowait, evt)

    thread = threading.Thread(
        target=workflow_service.execute_workflow,
        kwargs={"workflow_id": workflow_id, "on_event": on_event},
        daemon=True,
    )
    thread.start()

    try:
        while True:
            evt = await events.get()
            await websocket.send_text(json.dumps(evt))
            if evt.get("type") == "workflow_complete":
                break
    except WebSocketDisconnect:
        pass
    finally:
        thread.join(timeout=5)
