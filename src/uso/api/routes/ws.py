"""WebSocket endpoint for real-time log streaming."""

import asyncio
import queue

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from uso.services import run_service

router = APIRouter()


@router.websocket("/runs/{script_id}")
async def stream_run(ws: WebSocket, script_id: str, timeout: int = 60):
    """Execute a script and stream logs over WebSocket.

    Send a JSON message with `env` dict after connecting to start execution.
    """
    await ws.accept()

    try:
        # Receive env vars from client
        data = await ws.receive_json()
        env = data.get("env", {})
        timeout = data.get("timeout", timeout)

        log_queue: queue.Queue[str | None] = queue.Queue()
        run_id, thread = run_service.execute_script_async(
            script_id=script_id, env=env, timeout=timeout, log_queue=log_queue
        )

        await ws.send_json({"type": "started", "run_id": run_id})

        # Stream logs until sentinel (None) or thread finishes
        while thread.is_alive() or not log_queue.empty():
            try:
                line = log_queue.get(timeout=0.1)
                if line is None:
                    break
                await ws.send_json({"type": "log", "data": line})
            except queue.Empty:
                await asyncio.sleep(0.05)

        # Drain remaining
        while not log_queue.empty():
            line = log_queue.get_nowait()
            if line is not None:
                await ws.send_json({"type": "log", "data": line})

        thread.join(timeout=2)

        # Send final status
        run = run_service.get_run(run_id)
        await ws.send_json({
            "type": "complete",
            "run_id": run_id,
            "status": run.status if run else "unknown",
            "exit_code": run.exit_code if run else -1,
        })

    except WebSocketDisconnect:
        pass
    except ValueError as e:
        await ws.send_json({"type": "error", "detail": str(e)})
    finally:
        await ws.close()
