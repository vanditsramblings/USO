"""Modules endpoint — lists supported libraries per runtime with install status."""

import importlib.util
import subprocess
import sys

from fastapi import APIRouter

router = APIRouter()

# Catalogue of supported modules: {runtime: [{name, import_name, description, category}]}
_PYTHON_MODULES = [
    # HTTP / Networking
    {"name": "requests", "import_name": "requests", "description": "HTTP library — sync requests", "category": "network"},
    {"name": "httpx", "import_name": "httpx", "description": "Async-capable HTTP client", "category": "network"},
    {"name": "beautifulsoup4", "import_name": "bs4", "description": "HTML/XML parsing (scraping)", "category": "network"},
    {"name": "lxml", "import_name": "lxml", "description": "Fast XML/HTML processor", "category": "network"},
    # Data / IO
    {"name": "pandas", "import_name": "pandas", "description": "DataFrames for tabular data & CSV/Excel I/O", "category": "data"},
    {"name": "numpy", "import_name": "numpy", "description": "Numerical arrays and math", "category": "data"},
    {"name": "pyyaml", "import_name": "yaml", "description": "YAML read/write", "category": "data"},
    {"name": "toml", "import_name": "toml", "description": "TOML config file support", "category": "data"},
    {"name": "aiofiles", "import_name": "aiofiles", "description": "Async file I/O", "category": "io"},
    # Templates / Rendering
    {"name": "jinja2", "import_name": "jinja2", "description": "Templating engine (HTML, config, reports)", "category": "template"},
    {"name": "Pillow", "import_name": "PIL", "description": "Image creation and manipulation", "category": "media"},
    # CLI / UX
    {"name": "click", "import_name": "click", "description": "CLI argument parsing framework", "category": "cli"},
    {"name": "rich", "import_name": "rich", "description": "Rich terminal output (tables, progress bars)", "category": "cli"},
    {"name": "tqdm", "import_name": "tqdm", "description": "Progress bars for loops", "category": "cli"},
    # System
    {"name": "psutil", "import_name": "psutil", "description": "Process & system utilization metrics", "category": "system"},
    {"name": "python-dotenv", "import_name": "dotenv", "description": "Load .env files into os.environ", "category": "system"},
    # Standard lib highlights (always available)
    {"name": "pathlib", "import_name": "pathlib", "description": "Object-oriented filesystem paths", "category": "stdlib"},
    {"name": "threading", "import_name": "threading", "description": "Thread-based concurrency", "category": "stdlib"},
    {"name": "asyncio", "import_name": "asyncio", "description": "Async I/O event loop", "category": "stdlib"},
    {"name": "csv", "import_name": "csv", "description": "CSV read/write (stdlib)", "category": "stdlib"},
    {"name": "json", "import_name": "json", "description": "JSON encode/decode (stdlib)", "category": "stdlib"},
    {"name": "subprocess", "import_name": "subprocess", "description": "Spawn subprocesses, capture output", "category": "stdlib"},
    {"name": "os", "import_name": "os", "description": "OS interface, env vars, paths", "category": "stdlib"},
    {"name": "shutil", "import_name": "shutil", "description": "High-level file operations", "category": "stdlib"},
    {"name": "urllib", "import_name": "urllib", "description": "URL parsing and HTTP (stdlib)", "category": "stdlib"},
    {"name": "socket", "import_name": "socket", "description": "Low-level networking", "category": "stdlib"},
    {"name": "hashlib", "import_name": "hashlib", "description": "Cryptographic hashes (MD5, SHA-256…)", "category": "stdlib"},
    {"name": "datetime", "import_name": "datetime", "description": "Date & time arithmetic", "category": "stdlib"},
    {"name": "re", "import_name": "re", "description": "Regular expressions", "category": "stdlib"},
    {"name": "logging", "import_name": "logging", "description": "Structured logging", "category": "stdlib"},
]

_SHELL_BUILTINS = [
    {"name": "curl", "description": "HTTP requests from shell", "category": "network"},
    {"name": "wget", "description": "File download utility", "category": "network"},
    {"name": "jq", "description": "JSON processor for shell", "category": "data"},
    {"name": "awk", "description": "Text processing / column extraction", "category": "text"},
    {"name": "sed", "description": "Stream editor for text transformation", "category": "text"},
    {"name": "grep", "description": "Pattern search in text/files", "category": "text"},
    {"name": "find", "description": "Filesystem search", "category": "io"},
    {"name": "rsync", "description": "File synchronisation across hosts", "category": "io"},
    {"name": "tar", "description": "Archive creation and extraction", "category": "io"},
    {"name": "gzip", "description": "File compression", "category": "io"},
    {"name": "ssh", "description": "Secure remote shell", "category": "system"},
    {"name": "git", "description": "Version control operations", "category": "system"},
    {"name": "docker", "description": "Container management", "category": "system"},
    {"name": "cron", "description": "Job scheduling (system-level)", "category": "system"},
    {"name": "bc", "description": "Arbitrary precision calculator", "category": "math"},
    {"name": "column", "description": "Tabular text alignment", "category": "text"},
    {"name": "date", "description": "Date/time formatting", "category": "system"},
    {"name": "env", "description": "Print or set environment variables", "category": "system"},
]

_JS_MODULES = [
    {"name": "node:fs", "description": "File system (built-in)", "category": "io"},
    {"name": "node:path", "description": "Path manipulation (built-in)", "category": "io"},
    {"name": "node:http", "description": "HTTP server/client (built-in)", "category": "network"},
    {"name": "node:https", "description": "HTTPS (built-in)", "category": "network"},
    {"name": "node:os", "description": "OS info (built-in)", "category": "system"},
    {"name": "node:child_process", "description": "Spawn subprocesses (built-in)", "category": "system"},
    {"name": "node:crypto", "description": "Cryptographic utilities (built-in)", "category": "security"},
    {"name": "node:util", "description": "Utility functions (built-in)", "category": "stdlib"},
    {"name": "node:readline", "description": "Line-by-line CLI input (built-in)", "category": "cli"},
    {"name": "node:stream", "description": "Streaming data (built-in)", "category": "io"},
]


def _check_python_installed(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def _check_shell_available(cmd: str) -> bool:
    try:
        result = subprocess.run(["which", cmd], capture_output=True, timeout=2)
        return result.returncode == 0
    except Exception:
        return False


def _check_node_module(module: str) -> bool:
    """Node built-in modules are always available if node is installed."""
    if module.startswith("node:"):
        return _check_shell_available("node")
    return False


@router.get("/api/modules")
def list_modules() -> dict:
    """Return all supported modules per runtime with availability status."""
    python_modules = []
    for m in _PYTHON_MODULES:
        available = _check_python_installed(m["import_name"])
        python_modules.append({**m, "available": available, "runtime": "py"})

    shell_modules = []
    for m in _SHELL_BUILTINS:
        available = _check_shell_available(m["name"])
        shell_modules.append({**m, "available": available, "runtime": "sh"})

    node_available = _check_shell_available("node")
    js_modules = []
    for m in _JS_MODULES:
        js_modules.append({**m, "available": node_available, "runtime": "js"})

    return {
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "modules": python_modules,
        },
        "shell": {
            "modules": shell_modules,
        },
        "javascript": {
            "node_available": node_available,
            "modules": js_modules,
        },
    }
