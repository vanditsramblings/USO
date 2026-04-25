"""Seed predefined scripts and demo workflows into the database on first run."""

from pathlib import Path

from uso.db import init_db
from uso.services.script_service import get_script_by_name, register_script
from uso.services.workflow_service import create_workflow

_SCRIPTS_DIR = Path(__file__).parents[2] / "scripts" / "predefined"

_PREDEFINED: list[dict] = [
    {
        "name": "health_check",
        "runtime": "py",
        "description": "Call the USO /health endpoint and print a formatted report.",
        "file": "health_check.py",
        "tags": ["network", "monitoring", "demo", "python"],
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
        ],
    },
    {
        "name": "file_generator_demo",
        "runtime": "py",
        "description": "Generate JSON, CSV, YAML, and HTML output files — demonstrates file I/O and templating.",
        "file": "file_generator_demo.py",
        "tags": ["file", "demo", "python"],
        "parameters": [
            {"key": "OUTPUT_DIR", "is_secret": False},
            {"key": "FILE_PREFIX", "is_secret": False},
        ],
    },
    {
        "name": "env_chain_demo",
        "runtime": "sh",
        "description": "Read, transform, and forward env values between steps — demonstrates env chaining and defaults.",
        "file": "env_chain_demo.sh",
        "tags": ["demo", "automation", "shell"],
        "parameters": [
            {"key": "INPUT_FILE", "is_secret": False},
            {"key": "OUTPUT_FILE", "is_secret": False},
            {"key": "LOG_PREFIX", "is_secret": False},
            {"key": "STEP", "is_secret": False},
        ],
    },
    {
        "name": "metrics_export",
        "runtime": "py",
        "description": "Fetch /api/metrics and export all stats to a CSV file.",
        "file": "metrics_export.py",
        "tags": ["metrics", "reporting", "network", "python"],
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
        "tags": ["metrics", "reporting", "file", "shell"],
        "parameters": [
            {"key": "CSV_FILE", "is_secret": False},
        ],
    },
    {
        "name": "api_client_demo",
        "runtime": "js",
        "description": "Call the local USO API, list registered scripts, and summarise the runtime breakdown.",
        "file": "api_client_demo.js",
        "tags": ["network", "integration", "demo", "javascript"],
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
        ],
    },
    {
        "name": "list_scripts",
        "runtime": "py",
        "description": "List all registered scripts in a rich table. Optionally filter by runtime.",
        "file": "list_scripts.py",
        "tags": ["utility", "network", "python"],
        "parameters": [
            {"key": "BASE_URL", "is_secret": False},
            {"key": "FILTER_RUNTIME", "is_secret": False},
        ],
    },
    {
        "name": "system_info",
        "runtime": "sh",
        "description": "Print OS, CPU, memory, disk and tool availability for the execution environment.",
        "file": "system_info.sh",
        "tags": ["utility", "system", "shell"],
        "parameters": [],
    },
    {
        "name": "echo_times",
        "runtime": "sh",
        "description": "Echo a message N times — demonstrates simple parameter passing via env vars.",
        "file": "echo_times.sh",
        "tags": ["demo", "utility", "shell"],
        "parameters": [
            {"key": "REPEAT_COUNT", "is_secret": False},
            {"key": "MESSAGE", "is_secret": False},
        ],
    },
]


def seed_scripts() -> dict[str, str]:
    """Register predefined scripts if not already present. Returns {name: id}."""
    from uso.models import ParameterCreate, Runtime, ScriptCreate
    from uso.services.tag_service import get_or_create_tag, tag_script as tag_script_svc

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

        for tag_name in spec.get("tags", []):
            tag = get_or_create_tag(tag_name)
            tag_script_svc(script.id, tag.id)

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


def seed_file_pipeline_workflow(script_ids: dict[str, str]) -> None:
    """Create the File Output Chain workflow if not already present."""
    from uso.db.connection import get_connection

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM workflows WHERE name = 'File-Output-Chain'"
        ).fetchone()
        if row:
            return

    generator_id = script_ids.get("file_generator_demo")
    chain_id = script_ids.get("env_chain_demo")
    if not generator_id or not chain_id:
        return

    from uso import db

    wf_id = db.create_workflow(
        name="File-Output-Chain",
        description=(
            "Chained workflow: (1) file_generator_demo creates output files, "
            "(2) env_chain_demo reads the generated file and records a chain summary."
        ),
    )

    node1_id = db.add_node(
        workflow_id=wf_id,
        script_id=generator_id,
        position_x=100,
        position_y=150,
        config={"env": {"OUTPUT_DIR": "data/outputs", "FILE_PREFIX": "demo"}},
    )
    node2_id = db.add_node(
        workflow_id=wf_id,
        script_id=chain_id,
        position_x=400,
        position_y=150,
        config={"env": {
            "INPUT_FILE": "data/outputs/demo_report.json",
            "OUTPUT_FILE": "data/outputs/file_chain_result.txt",
            "STEP": "2",
        }},
    )
    db.add_workflow_edge(
        workflow_id=wf_id,
        source_node_id=node1_id,
        target_node_id=node2_id,
        condition=None,
    )
    print("  ✅ Seeded workflow: File-Output-Chain")


def seed_api_probe_workflow(script_ids: dict[str, str]) -> None:
    """Create the API Probe + Inventory workflow if not already present."""
    from uso.db.connection import get_connection

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM workflows WHERE name = 'API-Probe-Chain'"
        ).fetchone()
        if row:
            return

    health_id = script_ids.get("health_check")
    api_client_id = script_ids.get("api_client_demo")
    if not health_id or not api_client_id:
        return

    from uso import db

    wf_id = db.create_workflow(
        name="API-Probe-Chain",
        description=(
            "Chained workflow: (1) health_check verifies the app is running, "
            "(2) api_client_demo queries the API and summarises the script inventory."
        ),
    )

    node1_id = db.add_node(
        workflow_id=wf_id,
        script_id=health_id,
        position_x=100,
        position_y=150,
        config={"env": {"BASE_URL": "http://localhost:8000"}},
    )
    node2_id = db.add_node(
        workflow_id=wf_id,
        script_id=api_client_id,
        position_x=400,
        position_y=150,
        config={"env": {"BASE_URL": "http://localhost:8000"}},
    )
    db.add_workflow_edge(
        workflow_id=wf_id,
        source_node_id=node1_id,
        target_node_id=node2_id,
        condition=None,
    )
    print("  ✅ Seeded workflow: API-Probe-Chain")


_PREDEFINED_TAGS = [
    # capability
    "file", "network", "metrics", "scheduler", "utility",
    # language
    "python", "shell", "javascript",
    # intent
    "demo", "reporting", "orchestration", "integration", "automation",
    # legacy / domain
    "monitoring", "data-pipeline", "system", "etl",
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
    print("▶ Seeding demo workflows...")
    seed_workflow(ids)
    seed_file_pipeline_workflow(ids)
    seed_api_probe_workflow(ids)
    print("▶ Seed complete.")
