"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from uso import scheduler
from uso.db import init_db
from uso.seed import run_seed

from .routes import config, detect, edges, graph, health, metrics, modules, runs, schedules, scripts, tags, workflows, ws

_FRONTEND_BUILD = Path(__file__).parents[3] / "frontend" / "build"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    run_seed()
    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="USO — Unified Script Orchestrator",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(metrics.router, tags=["metrics"])
    app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(schedules.router, prefix="/api/schedules", tags=["schedules"])
    app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
    app.include_router(edges.router, prefix="/api/edges", tags=["edges"])
    app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
    app.include_router(detect.router, prefix="/api/detect", tags=["detect"])
    app.include_router(config.router, tags=["config"])
    app.include_router(modules.router, tags=["modules"])
    app.include_router(ws.router, prefix="/ws", tags=["websocket"])

    _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """Mount SvelteKit static build. Assets are served directly; all SPA
    routes fall back to index.html so client-side navigation works on refresh."""
    if not _FRONTEND_BUILD.exists():

        @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
        async def no_ui(full_path: str) -> HTMLResponse:
            return HTMLResponse(
                "<h1>UI not built</h1><p>Run: <code>cd frontend && npm run build</code></p>",
                status_code=503,
            )
        return

    # Hashed JS/CSS bundles under /_app — served with exact paths
    _app_dir = _FRONTEND_BUILD / "_app"
    if _app_dir.exists():
        app.mount("/_app", StaticFiles(directory=str(_app_dir)), name="spa_assets")

    # SPA catch-all: return index.html for every other path so
    # client-side routing works when a page is refreshed or linked directly
    _index = _FRONTEND_BUILD / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def serve_spa(full_path: str) -> FileResponse | HTMLResponse:
        if _index.exists():
            return FileResponse(_index)
        return HTMLResponse("<h1>index.html missing — rebuild the frontend</h1>", 404)


