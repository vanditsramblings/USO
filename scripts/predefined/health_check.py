"""USO Health Check — calls /health and prints a formatted report.

Parameters:
    BASE_URL: base URL of the USO API (default: http://localhost:8000)
"""

import json
import os
import sys

import requests

base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

try:
    resp = requests.get(f"{base_url}/health", timeout=10)
    resp.raise_for_status()
except requests.RequestException as e:
    print(f"ERROR: Could not reach {base_url}/health — {e}")
    sys.exit(1)

data = resp.json()
status = data.get("status", "unknown")
icon = "✅" if status == "ok" else "⚠️"

print(f"{icon}  USO Health Report")
print(f"   Status  : {status}")
print(f"   Version : {data.get('version', 'N/A')}")
print(f"   Uptime  : {data.get('uptime_seconds', 'N/A')}s")

if "process" in data:
    p = data["process"]
    print(f"   RSS     : {p.get('rss_mb', 'N/A')} MB")
    print(f"   CPU     : {p.get('cpu_percent', 'N/A')}%")

if "database" in data:
    db = data["database"]
    print(f"   DB      : {db.get('status', 'N/A')} — {db.get('size_bytes', 0):,} bytes")
    print(f"   Scripts : {db.get('scripts', 'N/A')}")
    print(f"   Runs    : {db.get('runs', 'N/A')}")

print()
print(json.dumps(data, indent=2))
