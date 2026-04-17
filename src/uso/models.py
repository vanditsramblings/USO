"""Pydantic models for USO API and service layer."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Runtime(StrEnum):
    py = "py"
    sh = "sh"
    js = "js"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failure = "failure"
    timeout = "timeout"


# --- Script ---


class ScriptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    runtime: Runtime
    content: str = Field(..., min_length=1)
    description: str = ""
    parameters: list["ParameterCreate"] = []


class ScriptUpdate(BaseModel):
    content: str | None = None
    description: str | None = None


class ScriptOut(BaseModel):
    id: str
    name: str
    runtime: Runtime
    content: str
    version: int
    description: str | None
    created_at: str
    updated_at: str
    parameters: list["ParameterOut"] = []


# --- Parameter ---


class ParameterCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Z_][A-Z0-9_]*$")
    is_secret: bool = False


class ParameterOut(BaseModel):
    id: str
    script_id: str
    key: str
    is_secret: bool


# --- Run ---


class RunCreate(BaseModel):
    script_id: str
    env: dict[str, str] = {}
    timeout: int = Field(default=60, ge=5, le=300)


class RunOut(BaseModel):
    id: str
    script_id: str
    status: RunStatus
    start_time: str | None
    end_time: str | None
    exit_code: int | None
    logs: str | None


# --- Artifact ---


class ArtifactOut(BaseModel):
    id: str
    run_id: str
    filename: str
    path: str
    sha256: str | None
    size_bytes: int | None
    created_at: str


# --- Health ---


class HealthOut(BaseModel):
    status: str = "ok"
    version: str


# --- Schedule ---


class TriggerType(StrEnum):
    cron = "cron"
    interval = "interval"
    date = "date"


class ScheduleCreate(BaseModel):
    script_id: str
    trigger_type: TriggerType
    trigger_args: dict = Field(..., min_length=1)
    misfire_grace_time: int = Field(default=60, ge=1, le=3600)


class ScheduleOut(BaseModel):
    id: str
    script_id: str
    trigger_type: TriggerType
    trigger_args: dict
    enabled: bool
    misfire_grace_time: int
    next_run_time: str | None = None
    created_at: str
