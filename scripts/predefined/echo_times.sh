#!/usr/bin/env bash
# ECHO_TIMES — repeat a string N times
# Parameters:
#   REPEAT_COUNT  — number of times to echo the string (default: 3)
#   MESSAGE       — the string to echo (default: "Hello from USO!")

COUNT="${REPEAT_COUNT:-3}"
MSG="${MESSAGE:-Hello from USO!}"

echo "Echoing message ${COUNT} time(s):"
for i in $(seq 1 "$COUNT"); do
  echo "[$i] $MSG"
done
