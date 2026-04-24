"""File Generator Demo — creates sample files in different formats.

Demonstrates: pathlib, json, csv, yaml, jinja2 templating, os.

Parameters:
    OUTPUT_DIR  : directory to write files (default: data/outputs)
    FILE_PREFIX : prefix for generated filenames (default: demo)
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

try:
    import yaml
    _yaml = True
except ImportError:
    _yaml = False

try:
    from jinja2 import Template
    _jinja = True
except ImportError:
    _jinja = False

output_dir = Path(os.environ.get("OUTPUT_DIR", "data/outputs"))
prefix = os.environ.get("FILE_PREFIX", "demo")
output_dir.mkdir(parents=True, exist_ok=True)
now = datetime.now().isoformat()

# 1. JSON
json_path = output_dir / f"{prefix}_data.json"
payload = {"generated_at": now, "items": [{"id": i, "value": i * 10} for i in range(1, 6)]}
json_path.write_text(json.dumps(payload, indent=2))
print(f"✅ JSON  → {json_path}")

# 2. CSV
csv_path = output_dir / f"{prefix}_data.csv"
with csv_path.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "value", "generated_at"])
    for i in range(1, 6):
        writer.writerow([i, i * 10, now])
print(f"✅ CSV   → {csv_path}")

# 3. YAML (if available)
if _yaml:
    yaml_path = output_dir / f"{prefix}_config.yaml"
    yaml_path.write_text(yaml.dump({"prefix": prefix, "output_dir": str(output_dir), "generated_at": now}))
    print(f"✅ YAML  → {yaml_path}")

# 4. HTML report (Jinja2)
if _jinja:
    tmpl = Template("""<!DOCTYPE html>
<html><head><title>{{ prefix }} Report</title></head>
<body>
<h1>{{ prefix }} Report</h1>
<p>Generated: {{ now }}</p>
<table border="1"><tr><th>ID</th><th>Value</th></tr>
{% for item in items %}<tr><td>{{ item.id }}</td><td>{{ item.value }}</td></tr>{% endfor %}
</table>
</body></html>""")
    html_path = output_dir / f"{prefix}_report.html"
    html_path.write_text(tmpl.render(prefix=prefix, now=now, items=payload["items"]))
    print(f"✅ HTML  → {html_path}")

print(f"\nAll files written to {output_dir}")
