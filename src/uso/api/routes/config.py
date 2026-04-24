"""Configuration API endpoints."""

from fastapi import APIRouter, HTTPException

from uso.config import AppConfig, get_config, save_config

router = APIRouter()


@router.get("/api/config")
def read_config() -> dict:
    """Return current application configuration."""
    return get_config().model_dump()


@router.patch("/api/config")
def update_config(patch: dict) -> dict:
    """Partially update configuration. Accepts any subset of the config schema."""
    cfg = get_config()
    try:
        merged = cfg.model_dump()
        # Deep merge top-level sections
        for section, values in patch.items():
            if section in merged and isinstance(values, dict):
                merged[section].update(values)
            else:
                merged[section] = values
        updated = AppConfig.model_validate(merged)
        save_config(updated)
        return updated.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/config/reset")
def reset_config() -> dict:
    """Reset configuration to defaults."""
    cfg = AppConfig()
    save_config(cfg)
    return cfg.model_dump()


@router.get("/api/config/schema")
def config_schema() -> dict:
    """Return the JSON schema for the configuration model."""
    return AppConfig.model_json_schema()
