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
    tags: list[str] = []


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
    tags: list["TagOut"] = []


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
    trigger: str = "manual"


# --- Metrics ---


class DurationPoint(BaseModel):
    run_id: str
    started_at: str | None
    duration_s: float | None
    status: str


class ScriptMetricsOut(BaseModel):
    total_runs: int
    success_rate: float  # 0.0–1.0
    avg_duration_s: float | None
    runs_by_status: dict[str, int]
    recent_durations: list[DurationPoint]  # last 20 finished runs


class WorkflowMetricsOut(BaseModel):
    total_runs: int
    success_rate: float
    avg_duration_s: float | None
    runs_by_status: dict[str, int]


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


# --- Tag ---


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")


class TagOut(BaseModel):
    id: str
    name: str
    created_at: str


# --- Edge (Knowledge Graph) ---


class EdgeRelation(StrEnum):
    data_flow = "data_flow"
    shared_env = "shared_env"
    manual = "manual"
    sequential = "sequential"


class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    relation: EdgeRelation
    metadata: dict | None = None


class EdgeOut(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation: EdgeRelation
    metadata: dict | None
    created_at: str


# --- Workflow (DAG) ---


class WorkflowNodeCreate(BaseModel):
    script_id: str
    position_x: float = 0
    position_y: float = 0
    config: dict | None = None


class WorkflowNodeUpdate(BaseModel):
    position_x: float | None = None
    position_y: float | None = None
    config: dict | None = None


class WorkflowEdgeCreate(BaseModel):
    source_node_id: str
    target_node_id: str
    condition: dict | None = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    description: str = ""
    nodes: list[WorkflowNodeCreate] = []
    edges: list[WorkflowEdgeCreate] = []


class WorkflowNodeOut(BaseModel):
    id: str
    workflow_id: str
    script_id: str
    position_x: float
    position_y: float
    config: dict | None


class WorkflowEdgeOut(BaseModel):
    id: str
    workflow_id: str
    source_node_id: str
    target_node_id: str
    condition: dict | None


class WorkflowOut(BaseModel):
    id: str
    name: str
    description: str | None
    nodes: list[WorkflowNodeOut] = []
    edges: list[WorkflowEdgeOut] = []
    created_at: str
    updated_at: str


# --- Workflow Runs ---


class WorkflowRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failure = "failure"


class NodeRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failure = "failure"
    skipped = "skipped"


class WorkflowNodeRunOut(BaseModel):
    id: str
    workflow_run_id: str
    node_id: str
    run_id: str | None
    status: NodeRunStatus
    execution_order: int


class WorkflowRunOut(BaseModel):
    id: str
    workflow_id: str
    status: WorkflowRunStatus
    started_at: str | None
    finished_at: str | None
    node_runs: list[WorkflowNodeRunOut] = []


# --- Auto-Detection ---


class DetectedParam(BaseModel):
    key: str
    is_secret: bool = False
    source: str  # 'argparse', 'environ', 'shell_var'


class DetectionResult(BaseModel):
    description: str
    parameters: list[DetectedParam] = []
    tags: list[str] = []
