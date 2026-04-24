"""MCP server — exposes registered scripts as tools for AI agents."""

from fastmcp import FastMCP

from uso import db
from uso.services import run_service, script_service

mcp = FastMCP(
    name="USO Script Orchestrator",
    instructions=(
        "Unified Script Orchestrator — discover & run managed scripts. "
        "Use list_scripts for discovery, get_script for schema details, "
        "and run_script to execute."
    ),
)


@mcp.tool()
def list_scripts() -> list[dict]:
    """List all registered scripts with name, runtime, and description."""
    scripts = script_service.list_scripts()
    return [
        {"id": s.id, "name": s.name, "runtime": s.runtime, "description": s.description}
        for s in scripts
    ]


@mcp.tool()
def get_script(script_id: str) -> dict | None:
    """Get full details of a script including parameters.

    Use this after list_scripts to get the parameter schema before execution.
    """
    s = script_service.get_script(script_id)
    if not s:
        return None
    return {
        "id": s.id,
        "name": s.name,
        "runtime": s.runtime,
        "version": s.version,
        "description": s.description,
        "parameters": [{"key": p.key, "is_secret": p.is_secret} for p in s.parameters],
    }


@mcp.tool()
def run_script(script_id: str, env: dict[str, str] | None = None, timeout: int = 60) -> dict:
    """Execute a registered script and return the run result.

    Args:
        script_id: The script UUID from list_scripts or get_script.
        env: Environment variables to inject (key-value pairs).
        timeout: Maximum execution time in seconds (5-300).
    """
    result = run_service.execute_script(script_id, env=env, timeout=timeout)
    return {
        "run_id": result.id,
        "status": result.status,
        "exit_code": result.exit_code,
        "logs": result.logs,
    }


@mcp.tool()
def get_run(run_id: str) -> dict | None:
    """Get the status and logs of a previous run."""
    r = run_service.get_run(run_id)
    if not r:
        return None
    return {
        "run_id": r.id,
        "script_id": r.script_id,
        "status": r.status,
        "exit_code": r.exit_code,
        "logs": r.logs,
    }


def main():
    """Run the MCP server (stdio transport)."""
    db.init_db()
    mcp.run()


if __name__ == "__main__":
    main()
