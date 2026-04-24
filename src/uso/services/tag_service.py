"""Tag service — business logic for tag management."""

from uso import db
from uso.models import TagCreate, TagOut


def create_tag(data: TagCreate) -> TagOut:
    tag_id = db.create_tag(name=data.name)
    return get_tag(tag_id)


def get_tag(tag_id: str) -> TagOut | None:
    row = db.get_tag(tag_id)
    return TagOut(**row) if row else None


def get_or_create_tag(name: str) -> TagOut:
    """Get existing tag by name or create it."""
    row = db.get_tag_by_name(name)
    if row:
        return TagOut(**row)
    tag_id = db.create_tag(name=name)
    return get_tag(tag_id)


def list_tags() -> list[TagOut]:
    return [TagOut(**r) for r in db.list_tags()]


def delete_tag(tag_id: str) -> bool:
    existing = db.get_tag(tag_id)
    if not existing:
        return False
    db.delete_tag(tag_id)
    return True


def tag_script(script_id: str, tag_id: str) -> None:
    db.tag_script(script_id, tag_id)


def untag_script(script_id: str, tag_id: str) -> None:
    db.untag_script(script_id, tag_id)


def get_script_tags(script_id: str) -> list[TagOut]:
    return [TagOut(**r) for r in db.get_script_tags(script_id)]
