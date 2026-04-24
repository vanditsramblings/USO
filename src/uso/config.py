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


class GraphConfig(BaseModel):
    """Force-simulation and viewport parameters for the knowledge graph."""

    # Force simulation
    link_distance_explicit: float = Field(default=140.0, ge=20.0, le=1000.0, description="Rest length for explicit edges")
    link_distance_implicit: float = Field(default=220.0, ge=20.0, le=1000.0, description="Rest length for implicit (shared-tag) edges")
    link_strength_explicit: float = Field(default=0.6, ge=0.0, le=1.0, description="Spring strength for explicit edges")
    link_strength_implicit: float = Field(default=0.3, ge=0.0, le=1.0, description="Spring strength for implicit edges")
    charge_strength: float = Field(default=-450.0, ge=-5000.0, le=0.0, description="Many-body repulsion (negative)")
    charge_distance_max: float = Field(default=400.0, ge=50.0, le=2000.0, description="Max distance for charge force")
    center_strength: float = Field(default=0.05, ge=0.0, le=1.0, description="Gravity toward center")
    alpha_decay: float = Field(default=0.028, ge=0.001, le=0.5, description="Simulation cooling rate")
    velocity_decay: float = Field(default=0.4, ge=0.0, le=1.0, description="Velocity damping per tick")
    # Viewport
    zoom_min: float = Field(default=0.1, ge=0.01, le=1.0, description="Minimum zoom scale")
    zoom_max: float = Field(default=3.0, ge=1.0, le=20.0, description="Maximum zoom scale")
    fit_view_delay_ms: int = Field(default=1800, ge=200, le=10000, description="Delay before auto-fitting view (ms)")
    # Implicit edges
    implicit_edge_min_shared_tags: int = Field(default=2, ge=1, le=20, description="Minimum shared tags to create implicit edge")
    # Performance
    collision_node_threshold: int = Field(default=80, ge=0, le=2000, description="Enable collision force when node count ≤ this")
    run_history_limit: int = Field(default=500, ge=10, le=5000, description="Max run records fetched for graph node sizing")


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)


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
