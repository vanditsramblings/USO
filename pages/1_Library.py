"""Script Library — Register, view, edit, and delete managed scripts."""

import streamlit as st

from uso.db import init_db
from uso.models import ParameterCreate, ScriptCreate, ScriptUpdate
from uso.services import script_service

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.header("📚 Script Library")

# --- Register New Script ---
with st.expander("➕ Register New Script", expanded=False):
    with st.form("register_script", clear_on_submit=True):
        name = st.text_input("Script Name", placeholder="e.g. backup-db")
        runtime = st.selectbox("Runtime", ["py", "sh", "js"])
        description = st.text_area("Description", placeholder="What does this script do?")
        content = st.text_area("Script Content", height=200, placeholder="Paste script code here")

        st.markdown("**Parameters** (comma-separated keys, prefix secret keys with `*`)")
        params_raw = st.text_input("Parameters", placeholder="e.g. API_URL, *API_KEY, LOG_LEVEL")

        submitted = st.form_submit_button("Register")
        if submitted:
            if not name or not content:
                st.error("Name and content are required.")
            else:
                try:
                    params = []
                    if params_raw.strip():
                        for p in params_raw.split(","):
                            p = p.strip()
                            if not p:
                                continue
                            is_secret = p.startswith("*")
                            key = p.lstrip("*").strip()
                            if key:
                                params.append(ParameterCreate(key=key, is_secret=is_secret))
                    data = ScriptCreate(
                        name=name.strip(),
                        runtime=runtime,
                        content=content,
                        description=description.strip(),
                        parameters=params,
                    )
                    script = script_service.register_script(data)
                    st.success(f"Registered **{script.name}** (id={script.id})")
                except Exception as e:
                    st.error(f"Registration failed: {e}")

# --- List Scripts ---
st.subheader("Registered Scripts")
scripts = script_service.list_scripts()

if not scripts:
    st.info("No scripts registered yet. Use the form above to add one.")
else:
    for script in scripts:
        with st.expander(f"**{script.name}** — {script.runtime} (v{script.version})"):
            st.markdown(f"**Description:** {script.description or '—'}")
            st.markdown(f"**Created:** {script.created_at} · **Updated:** {script.updated_at}")

            if script.parameters:
                st.markdown("**Parameters:**")
                for p in script.parameters:
                    secret_tag = " 🔒" if p.is_secret else ""
                    st.markdown(f"- `{p.key}`{secret_tag}")

            st.code(script.content, language=script.runtime)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Delete", key=f"del_{script.id}"):
                    script_service.delete_script(script.id)
                    st.rerun()
            with col2:
                if st.button("✏️ Edit", key=f"edit_{script.id}"):
                    st.session_state[f"editing_{script.id}"] = True

            if st.session_state.get(f"editing_{script.id}"):
                with st.form(f"edit_form_{script.id}"):
                    new_content = st.text_area("Updated Content", value=script.content, height=200)
                    new_desc = st.text_input("Updated Description", value=script.description or "")
                    if st.form_submit_button("Save"):
                        script_service.update_script(
                            script.id,
                            ScriptUpdate(content=new_content, description=new_desc or None),
                        )
                        st.session_state[f"editing_{script.id}"] = False
                        st.rerun()
