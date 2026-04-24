"""File management — uploads, versioned outputs, and post-execution hooks."""

import hashlib
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

UPLOAD_DIR = Path("data/uploads")
OUTPUT_DIR = Path("data/outputs")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def init_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sha256_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_upload(filename: str, data: bytes) -> dict:
    """Save an uploaded file. Returns {path, sha256, size_bytes}."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
    init_dirs()
    digest = sha256_digest(data)
    dest = UPLOAD_DIR / f"{digest[:12]}_{filename}"
    dest.write_bytes(data)
    return {"path": str(dest), "sha256": digest, "size_bytes": len(data)}


def get_output_dir(script_name: str, run_id: str) -> Path:
    """Create and return a versioned output directory for a run."""
    out = OUTPUT_DIR / script_name / run_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def collect_artifacts(output_dir: Path) -> list[dict]:
    """Scan an output directory and return metadata for all files."""
    if not output_dir.exists():
        return []
    artifacts = []
    for f in sorted(output_dir.iterdir()):
        if f.is_file():
            data = f.read_bytes()
            artifacts.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "sha256": sha256_digest(data),
                    "size_bytes": len(data),
                }
            )
    return artifacts


# --- Hooks ---


class Hook(ABC):
    @abstractmethod
    def fire(self, run_id: str, script_name: str, status: str, output_dir: Path) -> None:
        pass


class RetainHook(Hook):
    """Compress and move output to long-term storage on success."""

    def __init__(self, archive_dir: Path = Path("data/archives")):
        self.archive_dir = archive_dir

    def fire(self, run_id: str, script_name: str, status: str, output_dir: Path) -> None:
        if status != "success" or not output_dir.exists():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = self.archive_dir / f"{script_name}_{run_id}"
        shutil.make_archive(str(archive_path), "zip", output_dir)


class CleanupHook(Hook):
    """Remove output directory after run completion."""

    def fire(self, run_id: str, script_name: str, status: str, output_dir: Path) -> None:
        if output_dir.exists():
            shutil.rmtree(output_dir)


class NotifyHook(Hook):
    """Log a notification on failure (extendable to email/chat)."""

    def __init__(self, callback=None):
        self.callback = callback

    def fire(self, run_id: str, script_name: str, status: str, output_dir: Path) -> None:
        if status != "failure":
            return
        msg = f"Script '{script_name}' run {run_id} failed."
        if self.callback:
            self.callback(msg)


class VersionHook(Hook):
    """Collect artifacts and register them in the database."""

    def fire(self, run_id: str, script_name: str, status: str, output_dir: Path) -> None:
        from uso import db

        for art in collect_artifacts(output_dir):
            db.create_artifact(run_id=run_id, **art)
