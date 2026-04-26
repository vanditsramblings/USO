"""Run service — orchestrates script execution and run lifecycle."""

import queue
import threading

from uso import db
from uso.executor import SubprocessExecutor
from uso.models import RunOut

_executor = SubprocessExecutor()


def execute_script(
    script_id: str,
    env: dict[str, str] | None = None,
    timeout: int = 60,
    log_queue: queue.Queue | None = None,
    trigger: str = "manual",
) -> RunOut:
    """Execute a script and record the run."""
    script = db.get_script(script_id)
    if not script:
        raise ValueError(f"Script not found: {script_id}")

    run_id = db.create_run(script_id, trigger=trigger)
    db.update_run(run_id, status="running")

    if log_queue:
        result = _executor.run_streaming(
            script_content=script["content"].encode(),
            runtime=script["runtime"],
            log_queue=log_queue,
            env=env,
            timeout=timeout,
        )
        # Drain queue for logs
        lines = []
        while not log_queue.empty():
            item = log_queue.get_nowait()
            if item is not None:
                lines.append(item)
        logs = "".join(lines)
    else:
        result = _executor.run(
            script_content=script["content"].encode(),
            runtime=script["runtime"],
            env=env,
            timeout=timeout,
        )
        logs = result.get("logs", "")

    db.update_run(
        run_id,
        status=result["status"],
        exit_code=result.get("exit_code"),
        logs=logs,
    )
    return get_run(run_id)


def execute_script_async(
    script_id: str,
    env: dict[str, str] | None = None,
    timeout: int = 60,
    log_queue: queue.Queue | None = None,
    trigger: str = "manual",
) -> tuple[str, threading.Thread]:
    """Start script execution in a background thread. Returns (run_id, thread)."""
    script = db.get_script(script_id)
    if not script:
        raise ValueError(f"Script not found: {script_id}")

    run_id = db.create_run(script_id, trigger=trigger)
    db.update_run(run_id, status="running")

    def _run():
        try:
            if log_queue:
                result = _executor.run_streaming(
                    script_content=script["content"].encode(),
                    runtime=script["runtime"],
                    log_queue=log_queue,
                    env=env,
                    timeout=timeout,
                )
                log_queue.put(None)  # sentinel
            else:
                result = _executor.run(
                    script_content=script["content"].encode(),
                    runtime=script["runtime"],
                    env=env,
                    timeout=timeout,
                )
            db.update_run(
                run_id,
                status=result["status"],
                exit_code=result.get("exit_code"),
                logs=result.get("logs", ""),
            )
        except Exception as e:
            db.update_run(run_id, status="failure", exit_code=-1, logs=str(e))
            if log_queue:
                log_queue.put(None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return run_id, thread


def get_run(run_id: str) -> RunOut | None:
    runs = db.get_runs()
    for r in runs:
        if r["id"] == run_id:
            return RunOut(**r)
    return None


def list_runs(script_id: str | None = None, limit: int = 50) -> list[RunOut]:
    rows = db.get_runs(script_id=script_id, limit=limit)
    return [RunOut(**r) for r in rows]
