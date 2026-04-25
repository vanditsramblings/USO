#!/usr/bin/env bash
# env_chain_demo.sh — demonstrate env variable reading, defaults, and chaining.
# Env vars:
#   INPUT_FILE  — path to an optional input file (default: data/outputs/demo_report.json)
#   OUTPUT_FILE — where to write the chain result   (default: data/outputs/env_chain_result.txt)
#   LOG_PREFIX  — prefix for all log lines           (default: [env-chain])
#   STEP        — step number in the chain            (default: 1)
set -euo pipefail

INPUT_FILE="${INPUT_FILE:-data/outputs/demo_report.json}"
OUTPUT_FILE="${OUTPUT_FILE:-data/outputs/env_chain_result.txt}"
LOG_PREFIX="${LOG_PREFIX:-[env-chain]}"
STEP="${STEP:-1}"

echo "$LOG_PREFIX Step $STEP starting"
echo "$LOG_PREFIX Resolved environment:"
echo "  INPUT_FILE  = $INPUT_FILE"
echo "  OUTPUT_FILE = $OUTPUT_FILE"
echo "  LOG_PREFIX  = $LOG_PREFIX"
echo "  STEP        = $STEP"

# Summarise the input file if it exists
if [ -f "$INPUT_FILE" ]; then
  LINE_COUNT=$(wc -l < "$INPUT_FILE")
  SIZE=$(wc -c < "$INPUT_FILE")
  echo "$LOG_PREFIX Found input: $LINE_COUNT lines, $SIZE bytes"
else
  echo "$LOG_PREFIX Input file not found — running in standalone mode"
fi

# Write a summary record that a downstream script can consume
mkdir -p "$(dirname "$OUTPUT_FILE")"
{
  echo "step=$STEP"
  echo "input_file=$INPUT_FILE"
  echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "status=ok"
} > "$OUTPUT_FILE"

echo "$LOG_PREFIX Chain record written to $OUTPUT_FILE"
echo "$LOG_PREFIX Step $STEP complete."
