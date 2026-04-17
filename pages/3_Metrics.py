"""Metrics Dashboard — Execution trends and script performance."""

import streamlit as st

from uso.db import init_db
from uso.services import run_service, script_service

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.header("📊 Metrics Dashboard")

runs = run_service.list_runs(limit=200)
scripts = script_service.list_scripts()

if not runs:
    st.info("No execution history yet. Run a script from the **Execute** page.")
    st.stop()

# --- Summary Cards ---
total = len(runs)
success = sum(1 for r in runs if r.status == "success")
failed = sum(1 for r in runs if r.status == "failure")
timeouts = sum(1 for r in runs if r.status == "timeout")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Runs", total)
col2.metric("Successful", success)
col3.metric("Failed", failed)
col4.metric("Timeouts", timeouts)

# --- Status Distribution ---
st.subheader("Execution Status Distribution")
status_counts = {}
for r in runs:
    status_counts[r.status] = status_counts.get(r.status, 0) + 1
st.bar_chart(status_counts)

# --- Per-Script Breakdown ---
st.subheader("Runs by Script")
script_map = {s.id: s.name for s in scripts}
script_runs = {}
for r in runs:
    name = script_map.get(r.script_id, f"#{r.script_id[:8]}")
    script_runs[name] = script_runs.get(name, 0) + 1
st.bar_chart(script_runs)

# --- Recent Runs Table ---
st.subheader("Recent Runs")
table_data = []
for r in runs[:20]:
    table_data.append(
        {
            "Script": script_map.get(r.script_id, f"#{r.script_id[:8]}"),
            "Status": r.status,
            "Exit Code": r.exit_code,
            "Started": r.start_time,
            "Ended": r.end_time,
        }
    )
st.table(table_data)
