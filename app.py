"""USO — Unified Script Orchestrator. Streamlit entry point."""

import streamlit as st

from uso.db import init_db

st.set_page_config(
    page_title="USO — Script Orchestrator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB on first load
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

st.title("⚡ Unified Script Orchestrator")
st.markdown(
    "Centralized, secure, and observable script management "
    "for **Python**, **Shell**, and **JavaScript** runtimes."
)

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_Library.py", label="📚 Script Library", icon="📚")
with col2:
    st.page_link("pages/2_Execute.py", label="▶️ Execute Scripts", icon="▶️")
with col3:
    st.page_link("pages/3_Metrics.py", label="📊 Metrics Dashboard", icon="📊")
