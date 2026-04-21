"""App configuration — loaded from data/config.json, env-overridable."""

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_CONFIG_PATH = Path(os.getenv("USO_CONFIG_PATH", "data/config.json"))


class GeneralConfig(BaseModel):
    app_name: str = "USO"
    base_url: str = "http://localhost:8000"
    debug: bool = False


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["text", "json"] = "text"
    max_log_bytes: int = Field(default=1_048_576, ge=1024, description="Max bytes stored per run log")


class ExecutionConfig(BaseModel):
    default_timeout: int = Field(default=60, ge=5, le=3600)
    max_timeout: int = Field(default=300, ge=60, le=7200)
    max_concurrent_runs: int = Field(default=5, ge=1, le=50)
    allow_network: bool = True
    allowed_runtimes: list[Literal["py", "sh", "js"]] = ["py", "sh", "js"]


class PersistenceConfig(BaseModel):
    db_path: str = "data/uso.db"
    uploads_dir: str = "data/uploads"
    outputs_dir: str = "data/outputs"
    max_upload_bytes: int = Field(default=10_485_760, ge=1024)
    artifact_retention_days: int = Field(default=30, ge=1)


class SchedulerConfig(BaseModel):
    misfire_grace_seconds: int = Field(default=60, ge=1, le=3600)
    max_instances: int = Field(default=3, ge=1, le=20)
    coalesce: bool = True


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)


_config: AppConfig | None = None


def load_config() -> AppConfig:
    global _config
    if _config is not None:
        return _config
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text())
            _config = AppConfig.model_validate(data)
            return _config
        except Exception:
            pass  # fall through to default
    _config = AppConfig()
    return _config


def save_config(cfg: AppConfig) -> None:
    global _config
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(cfg.model_dump_json(indent=2))
    _config = cfg


def get_config() -> AppConfig:
    return load_config()
