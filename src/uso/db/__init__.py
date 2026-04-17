"""USO database layer — re-exports all CRUD operations."""

from .connection import DEFAULT_DB_PATH, _local, get_connection, init_db
from .runs import create_artifact, create_run, get_artifacts, get_runs, update_run
from .schedules import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    update_schedule_enabled,
)
from .scripts import (
    add_parameter,
    create_script,
    delete_parameter,
    delete_script,
    get_parameters,
    get_script,
    get_script_by_name,
    list_scripts,
    update_script,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "_local",
    "add_parameter",
    "create_artifact",
    "create_run",
    "create_schedule",
    "create_script",
    "delete_parameter",
    "delete_schedule",
    "delete_script",
    "get_artifacts",
    "get_connection",
    "get_parameters",
    "get_runs",
    "get_schedule",
    "get_script",
    "get_script_by_name",
    "init_db",
    "list_schedules",
    "list_scripts",
    "update_run",
    "update_schedule_enabled",
    "update_script",
]
