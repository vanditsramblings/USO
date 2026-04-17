"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from uso import scheduler
from uso.db import init_db

from .routes import health, runs, schedules, scripts


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="USO — Unified Script Orchestrator",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(schedules.router, prefix="/api/schedules", tags=["schedules"])
    return app
