"""Execute Scripts — Select, configure, and run scripts with real-time logs."""

import queue

import streamlit as st

from uso.db import init_db
from uso.services import run_service, script_service

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.header("▶️ Execute Script")

scripts = script_service.list_scripts()
if not scripts:
    st.info("No scripts registered. Go to **Library** to add one.")
    st.stop()

# Script selector
script_map = {s.name: s for s in scripts}
selected_name = st.selectbox("Select Script", options=list(script_map.keys()))
script = script_map[selected_name]

st.markdown(f"**Runtime:** `{script.runtime}` · **Version:** {script.version}")
if script.description:
    st.markdown(f"**Description:** {script.description}")

# Parameter inputs
env_values = {}
if script.parameters:
    st.subheader("Parameters")
    for p in script.parameters:
        input_type = "password" if p.is_secret else "default"
        val = st.text_input(
            f"{p.key} {'🔒' if p.is_secret else ''}",
            type=input_type,
            key=f"param_{p.id}",
        )
        if val:
            env_values[p.key] = val

# Timeout
timeout = st.number_input("Timeout (seconds)", min_value=5, max_value=300, value=60)

# Execute
run_key = f"running_{script.id}"
if st.button("▶️ Run Script", disabled=st.session_state.get(run_key, False)):
    st.session_state[run_key] = True

    log_queue: queue.Queue = queue.Queue()
    log_container = st.empty()
    status_container = st.empty()
    status_container.info("⏳ Running...")

    run_id, thread = run_service.execute_script_async(
        script_id=script.id,
        env=env_values or None,
        timeout=timeout,
        log_queue=log_queue,
    )

    # Stream logs
    collected_logs = []
    while True:
        try:
            line = log_queue.get(timeout=0.5)
        except queue.Empty:
            if not thread.is_alive():
                break
            continue
        if line is None:
            break
        collected_logs.append(line)
        log_container.code("".join(collected_logs), language="text")

    thread.join(timeout=5)

    # Fetch final run status
    run = run_service.get_run(run_id)
    if run and run.status == "success":
        status_container.success(f"✅ Completed (exit code: {run.exit_code})")
    elif run and run.status == "timeout":
        status_container.warning(f"⏱️ Timed out after {timeout}s")
    else:
        code = run.exit_code if run else -1
        status_container.error(f"❌ Failed (exit code: {code})")

    st.session_state[run_key] = False
