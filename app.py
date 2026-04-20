"""USO — Unified Script Orchestrator. WSGI/ASGI entry point.

Run with:  uvicorn app:app  OR  ./start.sh
"""

from uso.api.app import create_app

app = create_app()
