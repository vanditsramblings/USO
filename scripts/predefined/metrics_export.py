"""USO Metrics Export — fetches /api/metrics and exports to CSV.

Parameters:
    BASE_URL    : base URL of the USO API (default: http://localhost:8000)
    OUTPUT_FILE : path to write the CSV (default: data/outputs/metrics_export.csv)
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
output_file = os.environ.get("OUTPUT_FILE", "data/outputs/metrics_export.csv")

try:
    resp = requests.get(f"{base_url}/api/metrics", timeout=10)
    resp.raise_for_status()
except requests.RequestException as e:
    print(f"ERROR: Could not reach {base_url}/api/metrics — {e}")
    sys.exit(1)

data = resp.json()
now = datetime.now().isoformat()

rows = []

# Flatten scripts by runtime
for runtime, count in data.get("scripts", {}).get("by_runtime", {}).items():
    rows.append({"section": "scripts", "key": f"runtime.{runtime}", "value": str(count), "exported_at": now})
rows.append({"section": "scripts", "key": "total", "value": str(data.get("scripts", {}).get("total", 0)), "exported_at": now})

# Flatten runs by status
for status, count in data.get("runs", {}).get("by_status", {}).items():
    rows.append({"section": "runs", "key": f"status.{status}", "value": str(count), "exported_at": now})
rows.append({"section": "runs", "key": "total", "value": str(data.get("runs", {}).get("total", 0)), "exported_at": now})
rows.append({"section": "runs", "key": "avg_duration_seconds", "value": str(data.get("runs", {}).get("avg_duration_seconds", "")), "exported_at": now})

# Schedules
sched = data.get("schedules", {})
rows.append({"section": "schedules", "key": "total", "value": str(sched.get("total", 0)), "exported_at": now})
rows.append({"section": "schedules", "key": "enabled", "value": str(sched.get("enabled", 0)), "exported_at": now})

# Knowledge graph
kg = data.get("knowledge_graph", {})
for k, v in kg.items():
    rows.append({"section": "knowledge_graph", "key": k, "value": str(v), "exported_at": now})

# Storage
for k, v in data.get("storage", {}).items():
    rows.append({"section": "storage", "key": k, "value": str(v), "exported_at": now})

# Memory
for k, v in data.get("memory", {}).items():
    rows.append({"section": "memory", "key": k, "value": str(v), "exported_at": now})

out_path = Path(output_file)
out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["section", "key", "value", "exported_at"])
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Exported {len(rows)} metrics rows to {out_path}")
