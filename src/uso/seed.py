"""Seed predefined scripts and a demo workflow into the database on first run."""

from pathlib import Path

from uso.db import init_db
from uso.services.script_service import get_script_by_name, register_script
from uso.services.workflow_service import create_workflow

_SCRIPTS_DIR = Path(__file__).parents[2] / "scripts" / "predefined"

_PREDEFINED: list[dict] = [
    {
        "name": "echo_times",
        "runtime": "sh",
        "description": "Echo a message N times. Pass REPEAT_COUNT and MESSAGE env vars.",
        "file": "echo_times.sh",
        "parameters": [
            {"key": "REPEAT_COUNT", "is_secret": False},
            {"key": "MESSAGE", "is_secret": False},
        ],
    },
    {
        "name": "health_check",
        "runtime": "py",
        "description": "Call the USO /health endpoint and print a formatted report.",
        "file": "health_check.py",
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
        ],
    },
    {
        "name": "metrics_export",
        "runtime": "py",
        "description": "Fetch /api/metrics and export all stats to a CSV file.",
        "file": "metrics_export.py",
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
            {"key": "OUTPUT_FILE", "is_secret": False},
        ],
    },
    {
        "name": "process_metrics_csv",
        "runtime": "sh",
        "description": "Read the metrics CSV produced by metrics_export and print a summary table.",
        "file": "process_metrics_csv.sh",
        "parameters": [
            {"key": "CSV_FILE", "is_secret": False},
        ],
    },
    {
        "name": "list_scripts",
        "runtime": "py",
        "description": "List all registered scripts in a rich table. Optionally filter by runtime.",
        "file": "list_scripts.py",
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
            {"key": "FILTER_RUNTIME", "is_secret": False},
        ],
    },
    {
        "name": "file_generator_demo",
        "runtime": "py",
        "description": "Generate JSON, CSV, YAML, and HTML files — demonstrates file I/O and templating.",
        "file": "file_generator_demo.py",
        "parameters": [
            {"key": "OUTPUT_DIR", "is_secret": False},
            {"key": "FILE_PREFIX", "is_secret": False},
        ],
    },
    {
        "name": "system_info",
        "runtime": "sh",
        "description": "Print OS, CPU, memory, disk and tool availability for the execution environment.",
        "file": "system_info.sh",
        "parameters": [],
    },
]


def seed_scripts() -> dict[str, str]:
    """Register predefined scripts if not already present. Returns {name: id}."""
    ids: dict[str, str] = {}
    for spec in _PREDEFINED:
        existing = get_script_by_name(spec["name"])
        if existing:
            ids[spec["name"]] = existing.id
            continue
        content_path = _SCRIPTS_DIR / spec["file"]
        if not content_path.exists():
            continue
        content = content_path.read_text()
        from uso.models import ParameterCreate, Runtime, ScriptCreate

        script = register_script(
            ScriptCreate(
                name=spec["name"],
                runtime=Runtime(spec["runtime"]),
                content=content,
                description=spec["description"],
                parameters=[ParameterCreate(**p) for p in spec["parameters"]],
            )
        )
        ids[spec["name"]] = script.id
        print(f"  ✅ Seeded script: {spec['name']}")
    return ids


def seed_workflow(script_ids: dict[str, str]) -> None:
    """Create the demo metrics pipeline workflow if not already present."""
    from uso.db.connection import get_connection

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM workflows WHERE name = 'Metrics-Pipeline-Demo'"
        ).fetchone()
        if row:
            return

    export_id = script_ids.get("metrics_export")
    process_id = script_ids.get("process_metrics_csv")
    if not export_id or not process_id:
        return

    from uso import db
    from uso.models import WorkflowNodeCreate

    wf_id = db.create_workflow(
        name="Metrics-Pipeline-Demo",
        description=(
            "Chained workflow: (1) metrics_export generates a CSV, "
            "(2) process_metrics_csv reads it and prints a summary."
        ),
    )

    node1_id = db.add_node(
        workflow_id=wf_id,
        script_id=export_id,
        position_x=100,
        position_y=150,
        config={"env": {"OUTPUT_FILE": "data/outputs/metrics_export.csv"}},
    )
    node2_id = db.add_node(
        workflow_id=wf_id,
        script_id=process_id,
        position_x=400,
        position_y=150,
        config={"env": {"CSV_FILE": "data/outputs/metrics_export.csv"}},
    )
    db.add_workflow_edge(
        workflow_id=wf_id,
        source_node_id=node1_id,
        target_node_id=node2_id,
        condition=None,
    )
    print("  ✅ Seeded workflow: Metrics-Pipeline-Demo")


_PREDEFINED_TAGS = [
    "monitoring",
    "data-pipeline",
    "utility",
    "automation",
    "system",
    "demo",
    "etl",
    "reporting",
]


def seed_tags() -> None:
    """Create predefined tags if they don't already exist."""
    from uso.services.tag_service import get_or_create_tag

    for name in _PREDEFINED_TAGS:
        get_or_create_tag(name)
    print(f"  ✅ Ensured {len(_PREDEFINED_TAGS)} predefined tags")


def run_seed() -> None:
    init_db()
    print("▶ Seeding predefined tags...")
    seed_tags()
    print("▶ Seeding predefined scripts...")
    ids = seed_scripts()
    print("▶ Seeding demo workflow...")
    seed_workflow(ids)
    print("▶ Seed complete.")
