"""Schedules — Create, view, toggle, and delete scheduled script runs."""

import streamlit as st

from uso.db import init_db
from uso.models import ScheduleCreate
from uso.services import schedule_service, script_service

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.header("⏰ Schedules")

scripts = script_service.list_scripts()
if not scripts:
    st.info("Register scripts in the Library before creating schedules.")
    st.stop()

script_map = {s.name: s.id for s in scripts}

# --- Create Schedule ---
with st.expander("➕ New Schedule", expanded=False):
    with st.form("create_schedule", clear_on_submit=True):
        script_name = st.selectbox("Script", list(script_map.keys()))
        trigger_type = st.selectbox("Trigger Type", ["cron", "interval", "date"])
        st.markdown("**Trigger Arguments** (JSON key-value pairs)")

        col1, col2 = st.columns(2)
        if trigger_type == "cron":
            with col1:
                minute = st.text_input("minute", value="0")
                hour = st.text_input("hour", value="*")
            with col2:
                day_of_week = st.text_input("day_of_week", value="*")
        elif trigger_type == "interval":
            with col1:
                minutes = st.number_input("minutes", min_value=1, value=60)
        else:
            with col1:
                run_date = st.text_input("run_date", placeholder="2025-01-01 12:00:00")

        misfire = st.number_input("Misfire Grace (seconds)", min_value=1, value=60)
        submitted = st.form_submit_button("Create Schedule")
        if submitted:
            try:
                if trigger_type == "cron":
                    args = {"minute": minute, "hour": hour, "day_of_week": day_of_week}
                elif trigger_type == "interval":
                    args = {"minutes": int(minutes)}
                else:
                    args = {"run_date": run_date}
                data = ScheduleCreate(
                    script_id=script_map[script_name],
                    trigger_type=trigger_type,
                    trigger_args=args,
                    misfire_grace_time=int(misfire),
                )
                sched = schedule_service.create_schedule(data)
                st.success(f"Created schedule {sched.id[:8]}… for **{script_name}**")
            except Exception as e:
                st.error(f"Failed: {e}")

# --- List Schedules ---
st.subheader("Active Schedules")
schedules = schedule_service.list_schedules()

if not schedules:
    st.info("No schedules yet. Create one above.")
else:
    name_lookup = {s.id: s.name for s in scripts}
    for sched in schedules:
        sname = name_lookup.get(sched.script_id, sched.script_id[:8])
        status = "✅ Enabled" if sched.enabled else "⏸️ Paused"
        with st.expander(f"{sname} — {sched.trigger_type} [{status}]"):
            st.json(sched.trigger_args)
            st.text(f"Next run: {sched.next_run_time or 'N/A'}")
            st.text(f"Misfire grace: {sched.misfire_grace_time}s")

            col1, col2 = st.columns(2)
            with col1:
                label = "Pause" if sched.enabled else "Resume"
                if st.button(label, key=f"toggle_{sched.id}"):
                    schedule_service.toggle_schedule(sched.id, not sched.enabled)
                    st.rerun()
            with col2:
                if st.button("Delete", key=f"del_{sched.id}"):
                    schedule_service.delete_schedule(sched.id)
                    st.rerun()
