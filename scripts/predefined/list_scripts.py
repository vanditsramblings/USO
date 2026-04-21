"""USO Script Inventory — lists all registered scripts with their details.

Demonstrates: requests, pandas, rich table output, env parameters.

Parameters:
    BASE_URL : base URL of the USO API (default: http://localhost:8000)
    FILTER_RUNTIME : optional runtime filter — py, sh, or js (default: all)
"""

import os
import sys

import requests

try:
    from rich.console import Console
    from rich.table import Table
    _rich = True
except ImportError:
    _rich = False

base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
filter_runtime = os.environ.get("FILTER_RUNTIME", "").lower()

try:
    resp = requests.get(f"{base_url}/api/scripts", timeout=10)
    resp.raise_for_status()
except requests.RequestException as e:
    print(f"ERROR: {e}")
    sys.exit(1)

scripts = resp.json()
if filter_runtime:
    scripts = [s for s in scripts if s.get("runtime") == filter_runtime]

if not scripts:
    print("No scripts found.")
    sys.exit(0)

if _rich:
    console = Console()
    table = Table(title=f"USO Script Inventory ({len(scripts)} scripts)", show_lines=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Runtime", style="magenta")
    table.add_column("Version", justify="right")
    table.add_column("Description")
    table.add_column("Created At")
    for s in scripts:
        table.add_row(
            s.get("name", ""),
            s.get("runtime", ""),
            str(s.get("version", 1)),
            (s.get("description") or "")[:60],
            (s.get("created_at") or "")[:19],
        )
    console.print(table)
else:
    print(f"{'Name':<30} {'Runtime':<8} {'Version':<8} Description")
    print("-" * 80)
    for s in scripts:
        print(f"{s.get('name',''):<30} {s.get('runtime',''):<8} {str(s.get('version',1)):<8} {(s.get('description') or '')[:40]}")
