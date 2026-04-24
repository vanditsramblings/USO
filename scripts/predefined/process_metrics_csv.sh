#!/usr/bin/env bash
# Process Metrics CSV — reads a metrics CSV exported by metrics_export.py
# and prints a formatted summary table using awk.
# Parameters:
#   CSV_FILE : path to the CSV file (default: data/outputs/metrics_export.csv)

CSV="${CSV_FILE:-data/outputs/metrics_export.csv}"

if [ ! -f "$CSV" ]; then
  echo "ERROR: CSV file not found: $CSV"
  echo "Tip: run the 'metrics_export' Python script first."
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  USO Metrics Summary — $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

awk -F',' 'NR==1{next}
{
  section=$1; key=$2; value=$3
  printf "  %-20s %-35s %s\n", section, key, value
}' "$CSV"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Total rows: $(tail -n +2 "$CSV" | wc -l | tr -d ' ')"
