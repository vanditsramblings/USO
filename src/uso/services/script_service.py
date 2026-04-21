"""Script service — business logic for script CRUD."""

from uso import db
from uso.models import ParameterCreate, ParameterOut, ScriptCreate, ScriptOut, ScriptUpdate
from uso.services import tag_service


def register_script(data: ScriptCreate) -> ScriptOut:
    """Register a new script with parameters and optional tags."""
    script_id = db.create_script(
        name=data.name,
        runtime=data.runtime.value,
        content=data.content,
        description=data.description,
    )
    for p in data.parameters:
        db.add_parameter(script_id, p.key, is_secret=p.is_secret)
    for tag_name in data.tags:
        tag = tag_service.get_or_create_tag(tag_name)
        tag_service.tag_script(script_id, tag.id)
    return get_script(script_id)


def get_script(script_id: str) -> ScriptOut | None:
    """Get a script by ID with its parameters."""
    row = db.get_script(script_id)
    if not row:
        return None
    params = db.get_parameters(script_id)
    return ScriptOut(
        **row,
        parameters=[ParameterOut(**p) for p in params],
    )


def get_script_by_name(name: str) -> ScriptOut | None:
    row = db.get_script_by_name(name)
    if not row:
        return None
    params = db.get_parameters(row["id"])
    return ScriptOut(
        **row,
        parameters=[ParameterOut(**p) for p in params],
    )


def list_scripts() -> list[ScriptOut]:
    rows = db.list_scripts()
    result = []
    for row in rows:
        params = db.get_parameters(row["id"])
        result.append(ScriptOut(**row, parameters=[ParameterOut(**p) for p in params]))
    return result


def update_script(script_id: str, data: ScriptUpdate) -> ScriptOut | None:
    existing = db.get_script(script_id)
    if not existing:
        return None
    db.update_script(
        script_id,
        content=data.content if data.content is not None else existing["content"],
        description=data.description,
    )
    return get_script(script_id)


def delete_script(script_id: str) -> bool:
    existing = db.get_script(script_id)
    if not existing:
        return False
    db.delete_script(script_id)
    return True


def add_parameter(script_id: str, data: ParameterCreate) -> ParameterOut | None:
    existing = db.get_script(script_id)
    if not existing:
        return None
    db.add_parameter(script_id, data.key, is_secret=data.is_secret)
    params = db.get_parameters(script_id)
    return next((ParameterOut(**p) for p in params if p["key"] == data.key), None)


def delete_parameter(param_id: str) -> None:
    db.delete_parameter(param_id)
