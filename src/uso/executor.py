"""Script execution wrapper with resource limits and real-time log streaming."""

import os
import platform
import queue
import subprocess
import tempfile
import threading
from abc import ABC, abstractmethod
from pathlib import Path


class Executor(ABC):
    """Abstract base for script executors (Phase 1: subprocess, Phase 2: Docker)."""

    @abstractmethod
    def run(
        self,
        script_content: bytes,
        runtime: str,
        env: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> dict:
        """Execute script, return {exit_code, stdout, stderr}."""


# Runtime → (binary, file extension)
_RUNTIME_MAP = {
    "py": ("python3", ".py"),
    "sh": ("bash", ".sh"),
    "js": ("node", ".js"),
}

# Default resource limits (Phase 1)
_LIMITS = {
    "cpu_seconds": 30,
    "max_memory_bytes": 256 * 1024 * 1024,  # 256 MB
    "max_file_bytes": 10 * 1024 * 1024,  # 10 MB
}


def _set_resource_limits():
    """Pre-exec function to set resource limits (Unix only)."""
    if platform.system() == "Windows":
        return
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (_LIMITS["cpu_seconds"], _LIMITS["cpu_seconds"]))
        # RLIMIT_AS unreliable on macOS — skip if Darwin
        if platform.system() == "Linux":
            resource.setrlimit(
                resource.RLIMIT_AS, (_LIMITS["max_memory_bytes"], _LIMITS["max_memory_bytes"])
            )
        resource.setrlimit(
            resource.RLIMIT_FSIZE, (_LIMITS["max_file_bytes"], _LIMITS["max_file_bytes"])
        )
    except (ValueError, OSError):
        pass  # Best-effort; some limits unavailable on macOS


def _stream_pipe(pipe, log_queue: queue.Queue, prefix: str = ""):
    """Read lines from a pipe and push to queue."""
    for line in iter(pipe.readline, ""):
        log_queue.put(f"{prefix}{line}")
    pipe.close()


class SubprocessExecutor(Executor):
    """Execute scripts via subprocess with resource limits and log streaming."""

    def run(
        self,
        script_content: bytes,
        runtime: str,
        env: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> dict:
        if runtime not in _RUNTIME_MAP:
            raise ValueError(f"Unsupported runtime: {runtime}. Use: {list(_RUNTIME_MAP)}")

        binary, ext = _RUNTIME_MAP[runtime]
        log_queue: queue.Queue[str] = queue.Queue()

        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=ext, delete=False) as f:
            f.write(script_content)
            script_path = f.name

        # Build isolated env: only pass explicit vars + minimal PATH
        proc_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        if env:
            proc_env.update(env)

        try:
            proc = subprocess.Popen(
                [binary, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=proc_env,
                text=True,
                preexec_fn=_set_resource_limits if platform.system() != "Windows" else None,
            )

            # Stream stdout/stderr in background threads
            t_out = threading.Thread(target=_stream_pipe, args=(proc.stdout, log_queue, ""))
            t_err = threading.Thread(
                target=_stream_pipe, args=(proc.stderr, log_queue, "[stderr] ")
            )
            t_out.start()
            t_err.start()

            proc.wait(timeout=timeout)
            t_out.join(timeout=2)
            t_err.join(timeout=2)

            # Drain queue
            lines = []
            while not log_queue.empty():
                lines.append(log_queue.get_nowait())

            return {
                "exit_code": proc.returncode,
                "logs": "".join(lines),
                "status": "success" if proc.returncode == 0 else "failure",
            }

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            lines = []
            while not log_queue.empty():
                lines.append(log_queue.get_nowait())
            return {"exit_code": -1, "logs": "".join(lines), "status": "timeout"}

        except Exception as e:
            return {"exit_code": -1, "logs": str(e), "status": "failure"}

        finally:
            Path(script_path).unlink(missing_ok=True)

    def run_streaming(
        self,
        script_content: bytes,
        runtime: str,
        log_queue: queue.Queue,
        env: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> dict:
        """Same as run() but pushes logs to an external queue for real-time UI."""
        if runtime not in _RUNTIME_MAP:
            raise ValueError(f"Unsupported runtime: {runtime}")

        binary, ext = _RUNTIME_MAP[runtime]

        with tempfile.NamedTemporaryFile(mode="wb", suffix=ext, delete=False) as f:
            f.write(script_content)
            script_path = f.name

        proc_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        if env:
            proc_env.update(env)

        try:
            proc = subprocess.Popen(
                [binary, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=proc_env,
                text=True,
                preexec_fn=_set_resource_limits if platform.system() != "Windows" else None,
            )

            t_out = threading.Thread(target=_stream_pipe, args=(proc.stdout, log_queue, ""))
            t_err = threading.Thread(
                target=_stream_pipe, args=(proc.stderr, log_queue, "[stderr] ")
            )
            t_out.start()
            t_err.start()

            proc.wait(timeout=timeout)
            t_out.join(timeout=2)
            t_err.join(timeout=2)

            return {
                "exit_code": proc.returncode,
                "status": "success" if proc.returncode == 0 else "failure",
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return {"exit_code": -1, "status": "timeout"}
        except Exception as e:
            log_queue.put(f"[error] {e}\n")
            return {"exit_code": -1, "status": "failure"}
        finally:
            Path(script_path).unlink(missing_ok=True)
