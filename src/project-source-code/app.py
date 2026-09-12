"""
DC4X: Data Cleaning For You - Interactive Autonomous Analytics & Persistence Web Application
"""
import sys
import os
import io
import json
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.io as pio

# Add project-source-code to sys.path for robust imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import components.splash as splash_component
import components.login as login_component

from config.settings import (
    APP_BRAND,
    APP_DISPLAY_NAME,
    APP_TITLE,
    SUPPORTED_DOMAINS,
    DOMAIN_TAGLINES,
    GEMINI_MODEL,
    LLM_FREE_ONLY,
    LOGO_PATH,
    LOGO_DARK_PATH,
    LOGO_LIGHT_PATH,
    DATABASE_URL
)
from ingestion.loader import load_dataset, inspect_excel_sheets, DatasetIngestionError
from profiling.profiler import profile_dataset
from cleaning.cleaner import clean_dataset
from analysis.statistics import analyze_statistics
from analysis.anomalies import detect_anomalies
from visualization.automatic import generate_automatic_visualizations
from visualization.user_selected import build_custom_visualization, ChartValidationError
from reports.report_generator import (
    generate_non_ai_summary,
    generate_html_report,
    generate_pdf_report_bytes,
    build_table_summary
)
from models.result_models import OverallPipelineResult
from services.backend_client import BackendClient
from services.llm_service import GeminiService
from db.database import check_db_connection, get_db_safe_info

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session State Initialization
if "authenticated" not in st.session_state:
    # Show splash screen on first load
    if not st.session_state.get("splash_shown", False):
        splash_component.show()
        st.session_state.splash_shown = True
        st.rerun()

    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "selected_domain" not in st.session_state:
    st.session_state.selected_domain = SUPPORTED_DOMAINS[0]
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "backend_response" not in st.session_state:
    st.session_state.backend_response = None
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "🚀 Analysis Engine"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark Neon"
if "db_lock_state" not in st.session_state:
    st.session_state.db_lock_state = "LOCKED"  # Default lock after automated verification
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = "READY"
if "pipeline_error_msg" not in st.session_state:
    st.session_state.pipeline_error_msg = ""

is_dark = (st.session_state.theme_mode == "Dark Neon")

# Theme Stylesheet (Dark Neon vs Clean Light)
if is_dark:
    theme_css = """
    <style>
        .stApp {
            background-color: #0E0E12 !important;
            color: #F5EEDB !important;
            font-family: 'Inter', -apple-system, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #0E0E12 !important;
            border-right: 1px solid #1F1F2C !important;
            color: #F5EEDB !important;
        }
        section[data-testid="stSidebar"] * {
            color: #F5EEDB;
        }
        div[data-testid="stExpander"] {
            background-color: #14141C !important;
            border: 1px solid #282834 !important;
            border-radius: 8px !important;
        }
        .stButton button {
            background-color: #1A1A24 !important;
            color: #F5EEDB !important;
            border: 1px solid #2C2C3C !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }
        .stButton button:hover {
            border-color: #00E5FF !important;
            color: #00E5FF !important;
            box-shadow: 0 0 8px rgba(0, 229, 255, 0.3) !important;
        }
        button[data-baseweb="tab"] {
            color: #A09888 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #00E5FF !important;
            border-bottom: 2px solid #00E5FF !important;
        }
        div[role="radiogroup"] label, div[data-testid="stRadio"] label, div[data-testid="stRadio"] p {
            color: #F5EEDB !important;
            font-weight: 500 !important;
        }
        .brand-header-title {
            font-size: 2.2rem;
            font-weight: 900;
            letter-spacing: 1.5px;
            color: #F5EEDB;
            margin: 0;
            padding: 0;
        }
        .brand-header-title span { color: #00C3FF; }
        .brand-subtitle {
            font-size: 1.05rem;
            font-weight: 600;
            color: #B0A898;
            margin-top: 2px;
            margin-bottom: 15px;
        }
        .metric-card {
            background: #15151C;
            border: 1px solid #282834;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .metric-val { font-size: 1.8rem; font-weight: 800; color: #00E5FF; }
        .metric-lbl { font-size: 0.8rem; color: #A09888; text-transform: uppercase; letter-spacing: 0.6px; margin-top: 4px; font-weight: 600; }
        .step-header {
            background: #181822;
            color: #00E5FF;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 1.05rem;
            margin-top: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #00E5FF;
        }
        .summary-box {
            background-color: #14141C;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #00E676;
            font-size: 0.98rem;
            line-height: 1.6;
            border: 1px solid #242432;
            color: #E6DFD5;
        }
        .ai-summary-box {
            background-color: #171524;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #B388FF;
            font-size: 0.98rem;
            line-height: 1.6;
            border: 1px solid #302848;
            color: #F0EAFF;
        }
        .finding-card {
            background-color: #14141C;
            border: 1px solid #262636;
            border-left: 4px solid #00E5FF;
            border-radius: 6px;
            padding: 14px 18px;
            margin-bottom: 12px;
        }
        .finding-card-high { border-left-color: #FF4081; }
        .finding-card-medium { border-left-color: #FFD700; }
        .finding-card-info { border-left-color: #00E5FF; }
        .status-badge-ok { background-color: #064E3B; color: #6EE7B7; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
        .status-badge-warn { background-color: #78350F; color: #FDE68A; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
        .status-badge-err { background-color: #7F1D1D; color: #FECACA; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
    </style>
    """
else:
    theme_css = """
    <style>
        .stApp {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-family: 'Inter', -apple-system, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
            color: #0F172A !important;
        }
        section[data-testid="stSidebar"] * {
            color: #0F172A !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] {
            background-color: #F8FAFC !important;
            border: 1px solid #E2E8F0 !important;
        }
        div[data-testid="stExpander"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            color: #0F172A !important;
        }
        .stButton button {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease !important;
        }
        .stButton button:hover {
            border-color: #0284C7 !important;
            color: #0284C7 !important;
            background-color: #F0F9FF !important;
            box-shadow: 0 2px 6px rgba(2, 132, 199, 0.15) !important;
        }
        button[data-baseweb="tab"] {
            color: #475569 !important;
            font-weight: 600 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #0284C7 !important;
            border-bottom: 2px solid #0284C7 !important;
        }
        div[role="radiogroup"] label, div[data-testid="stRadio"] label, div[data-testid="stRadio"] p, div[data-testid="stRadio"] span {
            color: #0F172A !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-color: #CBD5E1 !important;
        }
        div[data-baseweb="input"] input, div[data-baseweb="base-input"] input {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border-color: #CBD5E1 !important;
        }
        .brand-header-title {
            font-size: 2.2rem;
            font-weight: 900;
            letter-spacing: 1.5px;
            color: #0F172A;
            margin: 0;
            padding: 0;
        }
        .brand-header-title span { color: #0284C7; }
        .brand-subtitle {
            font-size: 1.05rem;
            font-weight: 600;
            color: #64748B;
            margin-top: 2px;
            margin-bottom: 15px;
        }
        .metric-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .metric-val { font-size: 1.8rem; font-weight: 800; color: #0284C7; }
        .metric-lbl { font-size: 0.8rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.6px; margin-top: 4px; font-weight: 600; }
        .step-header {
            background: #EEF2FF;
            color: #4338CA;
            padding: 10px 16px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 1.05rem;
            margin-top: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #4F46E5;
        }
        .summary-box {
            background-color: #FFFFFF;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #059669;
            font-size: 0.98rem;
            line-height: 1.6;
            border: 1px solid #E2E8F0;
            color: #1E293B;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .ai-summary-box {
            background-color: #FAF5FF;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #7C3AED;
            font-size: 0.98rem;
            line-height: 1.6;
            border: 1px solid #E9D5FF;
            color: #3B0764;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .finding-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #0284C7;
            border-radius: 6px;
            padding: 14px 18px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.03);
            color: #0F172A;
        }
        .finding-card-high { border-left-color: #DC2626; }
        .finding-card-medium { border-left-color: #D97706; }
        .finding-card-info { border-left-color: #0284C7; }
        .status-badge-ok { background-color: #DCFCE7; color: #15803D; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
        .status-badge-warn { background-color: #FEF3C7; color: #B45309; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
        .status-badge-err { background-color: #FEE2E2; color: #B91C1C; padding: 3px 8px; border-radius: 4px; font-size: 0.78rem; font-weight: 700; }
    </style>
    """

st.markdown(theme_css, unsafe_allow_html=True)

backend_client = BackendClient()
health_info = backend_client.check_health()

# -------------------------------------------------------------
# 1. AUTHENTICATION SCREEN
# -------------------------------------------------------------
if not st.session_state.authenticated:
    login_component.render_login_page(is_dark)
    st.stop()

# Top Navigation Bar (Rendered only for authenticated users)
col_nav, col_user = st.columns([2.8, 1.7])

with col_nav:
    if st.session_state.authenticated:
        n_col1, n_col2, n_col3 = st.columns([1.1, 1.0, 1.3])
        with n_col1:
            if st.button("🚀 Analysis Engine", key="nav_btn_engine", type="primary" if st.session_state.app_mode == "🚀 Analysis Engine" else "secondary", use_container_width=True):
                st.session_state.app_mode = "🚀 Analysis Engine"
                st.rerun()
        with n_col2:
            if st.button("📜 Run History", key="nav_btn_history", type="primary" if st.session_state.app_mode == "📜 Run History" else "secondary", use_container_width=True):
                st.session_state.app_mode = "📜 Run History"
                st.rerun()
        with n_col3:
            if st.button("⚙️ System & Database", key="nav_btn_system", type="primary" if st.session_state.app_mode == "⚙️ System & Database" else "secondary", use_container_width=True):
                st.session_state.app_mode = "⚙️ System & Database"
                st.rerun()

with col_user:
    if st.session_state.authenticated:
        u_col1, u_col2 = st.columns([2.2, 1.0])
        with u_col1:
            st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; color: {'#F5EEDB' if is_dark else '#0F172A'}; padding-top: 6px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>👤 {st.session_state.username}</div>", unsafe_allow_html=True)
        with u_col2:
            if st.button("Logout", key="btn_logout", help="Sign out of DC4X", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.username = ""
                st.session_state.pipeline_result = None
                st.session_state.backend_response = None
                st.rerun()

# -------------------------------------------------------------
# 2. SYSTEM & DATABASE CONTROL VIEW
# -------------------------------------------------------------
if st.session_state.app_mode == "⚙️ System & Database":
    st.markdown("## ⚙️ DC4X System Diagnostics & Database Lock Controls")
    st.caption("Inspect live PostgreSQL connectivity, Google Gemini Free-Tier status, and lock database configuration.")

    db_safe = health_info.get("database", {})
    is_db_conn = db_safe.get("is_connected", False)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🗄️ PostgreSQL Database")
        lock_label = "🔒 LOCKED & ACTIVE" if st.session_state.db_lock_state == "LOCKED" else "✓ VERIFIED (UNLOCKED)" if st.session_state.db_lock_state == "VERIFIED" else "NOT VERIFIED"
        
        st.markdown(f"""
        - **Engine:** `{db_safe.get('engine', 'PostgreSQL')}`
        - **Host:** `{db_safe.get('host', 'localhost')}`
        - **Port:** `{db_safe.get('port', 5432)}`
        - **Database Name:** `{db_safe.get('database', 'datacleaning4u')}`
        - **User:** `{db_safe.get('username', 'postgres')}`
        - **Connection Status:** `{'CONNECTED' if is_db_conn else 'UNAVAILABLE'}`
        - **Database Lock:** `{lock_label}`
        """)

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            if st.button("🧪 Test Database Connection", key="btn_test_db"):
                conn_ok, conn_msg = check_db_connection()
                if conn_ok:
                    st.session_state.db_lock_state = "VERIFIED"
                    st.success(f"✓ {conn_msg} (Click Confirm & Lock below)")
                else:
                    st.session_state.db_lock_state = "UNVERIFIED"
                    st.error(f"✕ {conn_msg}")
        
        with t_col2:
            if st.session_state.db_lock_state != "LOCKED":
                if st.button("🔒 Confirm & Lock Database", key="btn_lock_db", help="Lock verified connection for persistence"):
                    conn_ok, _ = check_db_connection()
                    if conn_ok:
                        st.session_state.db_lock_state = "LOCKED"
                        st.success("🔒 Database configuration locked and active for run persistence!")
                        st.rerun()
                    else:
                        st.error("Cannot lock: connection test failed.")
            else:
                if st.button("🔓 Unlock / Reconfigure", key="btn_unlock_db", help="Unlock connection for modification"):
                    st.session_state.db_lock_state = "VERIFIED"
                    st.warning("Database configuration unlocked.")
                    st.rerun()

    with col2:
        st.markdown("### 🤖 Google Gemini Free-Tier LLM")
        gemini_cfg = health_info.get("gemini_configured", False)
        st.markdown(f"""
        - **Provider:** `Google Gemini API`
        - **Configured Model:** `{health_info.get('gemini_model', GEMINI_MODEL)}`
        - **Free-Tier Policy:** `{'ACTIVE (Zero Cost)' if LLM_FREE_ONLY else 'STANDARD'}`
        - **API Key Status:** `{'CONFIGURED (.env)' if gemini_cfg else 'MISSING'}`
        """)

        if st.button("🧪 Test Gemini API Connection", key="btn_test_llm"):
            gemini_service = GeminiService()
            llm_ok, llm_msg = gemini_service.test_connection()
            if llm_ok:
                st.success(f"✓ {llm_msg}")
            else:
                st.warning(f"⚠️ {llm_msg}")

    st.markdown("---")
    st.markdown("### 🌐 Backend API Infrastructure & Pipeline State")
    be_online = health_info.get("backend_online", False)
    st.info(f"**FastAPI / Uvicorn Service:** {'✓ ONLINE on Port 8000' if be_online else '⚠️ IN-PROCESS DIRECT RUNTIME'} | **Pipeline Engine Status:** `{st.session_state.pipeline_status}`")
    st.stop()

# -------------------------------------------------------------
# 3. RUN HISTORY VIEW
# -------------------------------------------------------------
if st.session_state.app_mode == "📜 Run History":
    st.markdown("## 📜 DC4X Analysis Run History")
    st.caption("Persistent record of all dataset analysis runs stored in PostgreSQL.")

    runs = backend_client.list_historical_runs(limit=50)

    if not runs:
        st.info("ℹ️ No historical runs recorded yet in PostgreSQL. Execute an analysis in the **Analysis Engine** to create a persistent record.")
    else:
        # Build tabular summary
        runs_table_data = []
        for r in runs:
            runs_table_data.append({
                "Run Code": r.get("run_code", "N/A"),
                "Timestamp": str(r.get("created_at", ""))[:19].replace("T", " "),
                "File Name": r.get("file_name", "dataset"),
                "Domain": r.get("domain", "General"),
                "Rows": f"{r.get('row_count', 0):,}",
                "Findings": r.get("findings_count", 0),
                "Quality Score": f"{r.get('data_quality_score', 100):.1f}",
                "AI Status": r.get("ai_status", "NONE"),
                "Status": r.get("status", "COMPLETED")
            })
        
        st.dataframe(pd.DataFrame(runs_table_data), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🔍 Inspect Historical Run Details")
        
        run_code_list = [r.get("run_code") for r in runs if r.get("run_code")]
        selected_code = st.selectbox("Choose a past Run to inspect (Read-Only):", run_code_list)

        if selected_code:
            detailed_run = backend_client.get_historical_run(selected_code)
            if detailed_run:
                st.markdown(f"#### 📋 Summary for **{detailed_run.get('run_code')}** ({detailed_run.get('file_name')})")
                
                # Metric Cards
                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1:
                    st.metric("Domain", detailed_run.get("domain", "General"))
                with rc2:
                    st.metric("Processed Rows", f"{detailed_run.get('row_count', 0):,}")
                with rc3:
                    st.metric("Total Findings", detailed_run.get("findings_count", 0))
                with rc4:
                    st.metric("Quality Score", f"{detailed_run.get('data_quality_score', 100):.1f} / 100")

                # AI Summary & Deterministic Summary
                ai_sum = detailed_run.get("ai_summary")
                if ai_sum and isinstance(ai_sum, dict):
                    st.markdown(f"""
                    <div class="ai-summary-box">
                        <div style="font-weight: 700; font-size: 1.05rem; color: {'#B388FF' if is_dark else '#7C3AED'}; margin-bottom: 8px;">
                            ✨ Stored Google Gemini AI Narrative ({GEMINI_MODEL})
                        </div>
                        <div>{ai_sum.get("overall_summary", "")}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    det_sum = detailed_run.get("deterministic_summary", "No summary recorded.")
                    st.markdown(f"""
                    <div class="summary-box">
                        <div style="font-weight: 700; font-size: 1.05rem; color: {'#00E676' if is_dark else '#059669'}; margin-bottom: 8px;">
                            📊 Stored Deterministic Analysis Summary
                        </div>
                        <div>{det_sum.replace(chr(10), "<br>")}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Findings List
                st.markdown("##### 💡 Evidence-Backed Findings")
                f_list = detailed_run.get("findings", [])
                if f_list:
                    for f in f_list:
                        sev = f.get("severity", "Info")
                        border_class = "finding-card-high" if sev == "High" else "finding-card-medium" if sev == "Medium" else "finding-card-info"
                        st.markdown(f"""
                        <div class="finding-card {border_class}">
                            <div style="font-weight: 700; font-size: 1rem;">
                                [{sev.upper()}] {f.get('title', '')}
                            </div>
                            <div style="margin-top: 4px;">{f.get('description', '')}</div>
                            <div style="font-size: 0.85rem; color: {'#00E5FF' if is_dark else '#0284C7'}; margin-top: 4px; font-style: italic;">
                                Evidence: {f.get('evidence', '')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("No specific high-severity findings recorded for this run.")

    st.stop()

# -------------------------------------------------------------
# 4. MAIN ANALYSIS ENGINE WORKFLOW
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ DC4X Control Panel")

    # Theme Switcher
    st.subheader("🎨 Visual Theme")
    theme_choice = st.radio(
        "Select Mode:",
        ["Dark Neon", "Clean Light"],
        index=0 if st.session_state.theme_mode == "Dark Neon" else 1,
        horizontal=True
    )
    if theme_choice != st.session_state.theme_mode:
        st.session_state.theme_mode = theme_choice
        st.rerun()

    # 1. System Health Status Panel
    with st.expander("🔌 System Health", expanded=True):
        be_badge = "status-badge-ok" if health_info.get("backend_online") else "status-badge-warn"
        be_text = "API ACTIVE (8000)" if health_info.get("backend_online") else "DIRECT RUNTIME"
        st.markdown(f"**Backend:** <span class='{be_badge}'>{be_text}</span>", unsafe_allow_html=True)

        is_locked = (st.session_state.db_lock_state == "LOCKED" and health_info.get("database", {}).get("is_connected"))
        db_badge = "status-badge-ok" if is_locked else "status-badge-warn" if health_info.get("database", {}).get("is_connected") else "status-badge-err"
        db_text = "POSTGRESQL LOCKED" if is_locked else "CONNECTED (UNLOCKED)" if health_info.get("database", {}).get("is_connected") else "OFFLINE"
        st.markdown(f"**Database:** <span class='{db_badge}'>{db_text}</span>", unsafe_allow_html=True)

        llm_badge = "status-badge-ok" if health_info.get("gemini_configured") else "status-badge-warn"
        llm_text = f"GEMINI ({GEMINI_MODEL})" if health_info.get("gemini_configured") else "NOT CONFIGURED"
        st.markdown(f"**LLM:** <span class='{llm_badge}'>{llm_text}</span>", unsafe_allow_html=True)

        pipe_badge = "status-badge-ok" if st.session_state.pipeline_status == "COMPLETED" else "status-badge-err" if st.session_state.pipeline_status == "FAILED" else "status-badge-warn"
        st.markdown(f"**Pipeline:** <span class='{pipe_badge}'>{st.session_state.pipeline_status}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # 2. Domain Selector
    st.subheader("1. Target Domain")
    chosen_domain = st.selectbox(
        "Select business context:",
        SUPPORTED_DOMAINS,
        index=SUPPORTED_DOMAINS.index(st.session_state.selected_domain)
    )
    if chosen_domain != st.session_state.selected_domain:
        st.session_state.selected_domain = chosen_domain
        st.session_state.pipeline_result = None
        st.session_state.backend_response = None
        st.session_state.pipeline_status = "READY"
        st.rerun()

    st.caption(f"ℹ️ {DOMAIN_TAGLINES.get(st.session_state.selected_domain, '')}")
    st.markdown("---")

    # 3. File Upload / Sample Datasets
    st.subheader("2. Ingestion Source")
    load_option = st.radio("Select data source:", ["Use Verified Sample", "Upload Custom File"])
    
    uploaded_file = None
    sample_file_path = None
    sheet_selected = None

    if load_option == "Upload Custom File":
        uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])
        if uploaded_file and uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            try:
                sheets = inspect_excel_sheets(uploaded_file)
                if len(sheets) > 1:
                    sheet_selected = st.selectbox("Select Excel Sheet:", sheets)
                else:
                    sheet_selected = sheets[0] if sheets else None
            except Exception as e:
                st.warning(f"Could not inspect workbook: {e}")
    else:
        sample_dict = {
            "Sales & Retail": "sales_sample.csv",
            "Finance & Banking": "finance_sample.xlsx",
            "Healthcare": "healthcare_sample.csv",
            "Human Resources (HR)": "hr_sample.csv"
        }
        chosen_sample = sample_dict.get(st.session_state.selected_domain, "sales_sample.csv")
        sample_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", chosen_sample))
        st.write(f"📁 Benchmark Sample: `{chosen_sample}`")
        if chosen_sample.endswith('.xlsx'):
            try:
                sheets = inspect_excel_sheets(sample_file_path)
                if len(sheets) > 1:
                    sheet_selected = st.selectbox("Select Sheet:", sheets)
                else:
                    sheet_selected = sheets[0] if sheets else None
            except Exception:
                pass

    st.markdown("---")

# Main Content Tabs for Analysis Engine
tabs = st.tabs([
    "📥 Ingestion & Profiling",
    "🧹 Data Cleaning",
    "📊 Statistical Engine",
    "⚠️ Anomaly Audit",
    "📈 Visualizations & Custom Builder",
    "🤖 Executive & AI Summary"
])

file_input = uploaded_file or sample_file_path

if not file_input:
    st.info("👈 Please select or upload a dataset using the sidebar to begin analysis.")
    st.stop()

# Execute Full Pipeline
try:
    fname = uploaded_file.name if uploaded_file else os.path.basename(sample_file_path)
    raw_df, meta = load_dataset(file_input, fname, sheet_name=sheet_selected)
    
    st.session_state.raw_df = raw_df

    # Profile raw dataset
    profile = profile_dataset(
        raw_df,
        file_name=meta["file_name"],
        file_type=meta["file_type"],
        file_size_bytes=meta["file_size_bytes"],
        domain=st.session_state.selected_domain
    )
    
    # Clean dataset
    cleaned_df, cleaning_rep = clean_dataset(raw_df, profile)
    st.session_state.cleaned_df = cleaned_df

    # Profile cleaned dataset
    cleaned_profile = profile_dataset(
        cleaned_df,
        file_name=meta["file_name"],
        file_type=meta["file_type"],
        file_size_bytes=meta["file_size_bytes"],
        domain=st.session_state.selected_domain
    )

    # Anomaly Detection
    anomaly_rep = detect_anomalies(cleaned_df, cleaned_profile)

    # Statistical Analysis
    analysis_rep = analyze_statistics(
        cleaned_df,
        cleaned_profile,
        anomaly_report=anomaly_rep,
        domain=st.session_state.selected_domain
    )

    # Automatic Visualizations
    auto_charts = generate_automatic_visualizations(
        cleaned_df,
        cleaned_profile,
        analysis_rep,
        domain=st.session_state.selected_domain,
        theme_mode="light" if not is_dark else "dark"
    )

    # Table-wise summary
    table_sum = build_table_summary(
        table_name=sheet_selected or fname,
        profile=cleaned_profile,
        cleaning=cleaning_rep,
        analysis=analysis_rep,
        anomaly=anomaly_rep
    )

    # Deterministic Non-AI Executive Summary
    summary_text = generate_non_ai_summary(
        domain=st.session_state.selected_domain,
        profile=cleaned_profile,
        cleaning=cleaning_rep,
        analysis=analysis_rep,
        anomaly=anomaly_rep,
        findings=analysis_rep.findings
    )

    # Build Overall Result with robust field compatibility
    pipeline_result = OverallPipelineResult(
        domain=st.session_state.selected_domain,
        file_name=fname,
        sheet_name=sheet_selected,
        profile=cleaned_profile,
        cleaning_report=cleaning_rep,
        analysis_report=analysis_rep,
        anomaly_report=anomaly_rep,
        automatic_charts=auto_charts,
        visualizations=auto_charts,
        summary_text=summary_text,
        overall_summary=summary_text,
        table_summaries=[table_sum],
        findings=analysis_rep.findings
    )
    st.session_state.pipeline_result = pipeline_result
    st.session_state.pipeline_status = "COMPLETED"

    # Persist to PostgreSQL and synthesize AI narrative (cached in session)
    if st.session_state.backend_response is None or st.session_state.backend_response.get("file_name") != fname:
        with st.spinner("Persisting analysis to PostgreSQL and synthesizing AI narrative..."):
            st.session_state.backend_response = backend_client.submit_analysis_run(
                pipeline_result.to_serializable_dict(),
                trigger_ai_summary=True
            )

except DatasetIngestionError as die:
    st.session_state.pipeline_status = "FAILED"
    st.session_state.pipeline_error_msg = str(die)
    st.error(f"❌ Ingestion Error: {die}")
    st.stop()
except Exception as ex:
    st.session_state.pipeline_status = "FAILED"
    st.session_state.pipeline_error_msg = str(ex)
    st.error(f"❌ Analysis Pipeline Failure: {ex}")
    st.stop()

# -------------------------------------------------------------
# TAB 1: INGESTION & PROFILING
# -------------------------------------------------------------
with tabs[0]:
    st.markdown('<div class="step-header">📥 Dataset Ingestion & Profiling Overview</div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{profile.total_rows:,}</div><div class="metric-lbl">Total Rows</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{profile.total_columns}</div><div class="metric-lbl">Total Columns</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{profile.missing_cells:,}</div><div class="metric-lbl">Missing Cells</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{profile.duplicate_rows:,}</div><div class="metric-lbl">Duplicate Rows</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Ingested Raw Data Preview")
    st.dataframe(raw_df.head(25), use_container_width=True)

    st.subheader("🔍 Column Semantic Profiling & Inferred Types")
    col_prof_data = []
    for cname, cinfo in profile.columns.items():
        col_prof_data.append({
            "Column": cname,
            "Inferred Type": cinfo.inferred_type,
            "Null Count": cinfo.missing_count,
            "Null %": f"{cinfo.missing_pct:.1f}%",
            "Unique Values": cinfo.unique_count,
            "Sample Values": ", ".join(map(str, cinfo.sample_values[:3]))
        })
    st.dataframe(pd.DataFrame(col_prof_data), use_container_width=True)

# -------------------------------------------------------------
# TAB 2: DATA CLEANING
# -------------------------------------------------------------
with tabs[1]:
    st.markdown('<div class="step-header">🧹 Data Hygiene & Cleaning Operations</div>', unsafe_allow_html=True)
    
    cl1, cl2, cl3 = st.columns(3)
    with cl1:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{cleaning_rep.duplicates_removed}</div><div class="metric-lbl">Duplicates Removed</div></div>""", unsafe_allow_html=True)
    with cl2:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{cleaning_rep.total_missing_handled}</div><div class="metric-lbl">Missing Cells Handled</div></div>""", unsafe_allow_html=True)
    with cl3:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{cleaning_rep.rows_after:,}</div><div class="metric-lbl">Cleaned Records</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🛠️ Remediation Actions Applied")
    steps = cleaning_rep.cleaning_steps if hasattr(cleaning_rep, "cleaning_steps") and cleaning_rep.cleaning_steps else getattr(cleaning_rep, "actions", [])
    if steps:
        for action in steps:
            if isinstance(action, dict):
                act_name = action.get("step", action.get("action_type", "Remediation"))
                details = action.get("details", [])
                det_str = "; ".join(details) if isinstance(details, list) and details else action.get("description", "")
                st.write(f"- ✅ **{act_name}:** {det_str}")
            else:
                act_type = getattr(action, "action_type", "Remediation")
                act_desc = getattr(action, "description", str(action))
                st.write(f"- ✅ **{act_type}:** {act_desc}")
    else:
        st.info("No cleaning transformations required. Dataset was already standardized.")

    st.subheader("✨ Cleaned Transformed Dataset Preview")
    st.dataframe(cleaned_df.head(25), use_container_width=True)

# -------------------------------------------------------------
# TAB 3: STATISTICAL ENGINE & FINDINGS
# -------------------------------------------------------------
with tabs[2]:
    st.markdown('<div class="step-header">📊 Statistical Engine & Domain Findings</div>', unsafe_allow_html=True)

    st.subheader("💡 Verified Evidence-Backed Findings")
    if pipeline_result.findings:
        for f in pipeline_result.findings:
            sev = f.severity
            border_class = "finding-card-high" if sev == "High" else "finding-card-medium" if sev == "Medium" else "finding-card-info"
            st.markdown(f"""
            <div class="finding-card {border_class}">
                <div style="font-weight: 700; font-size: 1.05rem;">
                    [{sev.upper()}] {f.title}
                </div>
                <div style="margin-top: 4px;">{f.description}</div>
                <div style="font-size: 0.85rem; color: {'#00E5FF' if is_dark else '#0284C7'}; margin-top: 4px; font-style: italic;">
                    Evidence: {f.evidence}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No high-severity findings discovered.")

    st.markdown("---")
    st.subheader("📈 Numerical Distributions & Summary Statistics")
    if analysis_rep.numerical_summary:
        num_summary_df = pd.DataFrame(analysis_rep.numerical_summary).T
        st.dataframe(num_summary_df, use_container_width=True)

# -------------------------------------------------------------
# TAB 4: ANOMALY AUDIT
# -------------------------------------------------------------
with tabs[3]:
    st.markdown('<div class="step-header">⚠️ Anomaly Detection & Risk Audit</div>', unsafe_allow_html=True)

    a1, a2, a3 = st.columns(3)
    with a1:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{anomaly_rep.total_anomalies_found}</div><div class="metric-lbl">Total Anomalies</div></div>""", unsafe_allow_html=True)
    with a2:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{len(anomaly_rep.outliers_by_column)}</div><div class="metric-lbl">Columns with Outliers</div></div>""", unsafe_allow_html=True)
    with a3:
        st.markdown(f"""<div class="metric-card"><div class="metric-val">{len(anomaly_rep.multivariate_anomalies)}</div><div class="metric-lbl">Multivariate Anomalies</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    if anomaly_rep.items:
        st.subheader("🚨 Identified Anomalous Observations")
        anom_rows = []
        for item in anomaly_rep.items[:30]:
            anom_rows.append({
                "Column": item.column,
                "Row Index": item.row_index,
                "Observed Value": str(item.value),
                "Method": item.method,
                "Severity": item.severity,
                "Reason": item.reason
            })
        st.dataframe(pd.DataFrame(anom_rows), use_container_width=True)
    else:
        st.success("✓ No anomalous observations detected in this dataset.")

# -------------------------------------------------------------
# TAB 5: VISUALIZATIONS & CUSTOM BUILDER
# -------------------------------------------------------------
with tabs[4]:
    st.markdown('<div class="step-header">📈 Visualizations & Chart Builder</div>', unsafe_allow_html=True)

    # 1. Automatic Charts
    st.subheader("🤖 Automatically Curated Visualizations")
    if auto_charts:
        for chart in auto_charts:
            st.plotly_chart(chart.figure, use_container_width=True)
            st.caption(f"💡 **Takeaway:** {chart.key_takeaway}")
            st.markdown("---")
    else:
        st.info("No automatic charts could be generated for this data shape.")

    # 2. Custom Chart Builder
    st.subheader("🎨 Custom Chart Builder")
    with st.expander("🛠️ Configure Custom Visualization", expanded=False):
        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        with b_c1:
            custom_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Scatter Plot", "Box Plot", "Histogram", "Pie Chart"])
        with b_c2:
            custom_x = st.selectbox("X Axis Column", [None] + list(cleaned_df.columns), index=1 if len(cleaned_df.columns) > 0 else 0)
        with b_c3:
            custom_y = st.selectbox("Y Axis Column", [None] + list(cleaned_df.columns), index=2 if len(cleaned_df.columns) > 1 else 0)
        with b_c4:
            custom_grp = st.selectbox("Group / Color By", ["None"] + list(cleaned_df.columns))

        if st.button("Generate Custom Chart", key="btn_custom_chart"):
            try:
                custom_result = build_custom_visualization(
                    df=cleaned_df,
                    profile=cleaned_profile,
                    chart_type=custom_type,
                    x_col=custom_x,
                    y_col=custom_y,
                    group_col=custom_grp,
                    theme_mode="light" if not is_dark else "dark"
                )
                st.plotly_chart(custom_result.figure, use_container_width=True)
                st.success(f"✓ {custom_result.key_takeaway}")
            except ChartValidationError as cve:
                st.warning(f"⚠️ {cve}")
            except Exception as e:
                st.error(f"✕ Could not render custom chart: {e}")

# -------------------------------------------------------------
# TAB 6: EXECUTIVE & AI SUMMARY
# -------------------------------------------------------------
with tabs[5]:
    st.markdown('<div class="step-header">🤖 Executive AI Explanation & Diagnostic Summary</div>', unsafe_allow_html=True)

    be_res = st.session_state.backend_response or {}
    ai_summary_obj = be_res.get("ai_summary")
    ai_status = be_res.get("ai_status", "NONE")
    run_code_val = be_res.get("run_code") or be_res.get("run_id", "N/A")

    # If AI summary is available from Google Gemini Free-Tier
    if ai_summary_obj and isinstance(ai_summary_obj, dict):
        st.markdown(f"""
        <div class="ai-summary-box">
            <div style="font-weight: 700; font-size: 1.15rem; color: {'#B388FF' if is_dark else '#7C3AED'}; margin-bottom: 8px;">
                ✨ Google Gemini AI Executive Narrative ({GEMINI_MODEL} - Free Tier)
            </div>
            <div>{ai_summary_obj.get("overall_summary", "")}</div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("💡 Strategic Key Findings (AI Synthesized)")
        for takeaway in ai_summary_obj.get("key_findings", []):
            st.write(f"- 📌 {takeaway}")

        if ai_summary_obj.get("anomalies"):
            st.subheader("⚠️ Critical Risk & Outlier Interpretations")
            for anom_item in ai_summary_obj.get("anomalies", []):
                if isinstance(anom_item, dict):
                    st.write(f"- **{anom_item.get('finding', 'Observation')}:** {anom_item.get('explanation', '')}")

        if ai_summary_obj.get("data_quality_notes"):
            st.subheader("🧹 Data Hygiene & Formatting Notes")
            for dq_note in ai_summary_obj.get("data_quality_notes", []):
                st.write(f"- ℹ️ {dq_note}")

    else:
        # Fallback guidance
        if ai_status == "UNCONFIGURED":
            st.info("💡 **Google Gemini API Key is not configured in `.env`**. Displaying deterministic analysis summary below.")
        elif ai_status == "RATE_LIMIT_QUOTA_EXCEEDED":
            st.warning("⚠️ **Gemini Free-Tier rate limit reached**. Reverting to deterministic summary below.")
        elif ai_status == "API_ERROR":
            st.warning(f"⚠️ **Gemini API Error**. Showing deterministic summary below.")

        st.markdown(f'<div class="summary-box">{summary_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="step-header">📋 Table-Wise Diagnostic Scorecard & Persistence Run</div>', unsafe_allow_html=True)
    
    for t_sum in st.session_state.pipeline_result.table_summaries:
        ts1, ts2, ts3, ts4 = st.columns(4)
        with ts1:
            st.metric("Table / Sheet", t_sum.table_name)
        with ts2:
            st.metric("Data Quality Score", f"{t_sum.data_quality_score} / 100")
        with ts3:
            st.metric("Anomalies Flagged", t_sum.anomaly_count)
        with ts4:
            st.metric("Database Run Code", str(run_code_val))

    st.markdown("---")
    st.markdown('<div class="step-header">📥 DC4X Export & Download Center</div>', unsafe_allow_html=True)

    d1, d2, d3, d4 = st.columns(4)

    # 1. Cleaned CSV
    csv_bytes = cleaned_df.to_csv(index=False).encode('utf-8')
    with d1:
        st.download_button(
            label="📄 Download Cleaned CSV",
            data=csv_bytes,
            file_name=f"dc4x_cleaned_{fname}.csv",
            mime="text/csv"
        )

    # 2. Cleaned XLSX
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine='openpyxl') as writer:
        cleaned_df.to_excel(writer, sheet_name="CleanedData", index=False)
    xlsx_bytes = xlsx_buffer.getvalue()
    with d2:
        st.download_button(
            label="📊 Download Cleaned XLSX",
            data=xlsx_bytes,
            file_name=f"dc4x_cleaned_{fname}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 3. HTML Audit Report
    html_report_str = generate_html_report(st.session_state.pipeline_result)
    with d3:
        st.download_button(
            label="🌐 Download HTML Report",
            data=html_report_str.encode('utf-8'),
            file_name=f"dc4x_report_{fname}.html",
            mime="text/html"
        )

    # 4. PDF Audit Report
    pdf_report_bytes = generate_pdf_report_bytes(st.session_state.pipeline_result)
    with d4:
        st.download_button(
            label="📕 Download PDF Report",
            data=pdf_report_bytes,
            file_name=f"dc4x_report_{fname}.pdf",
            mime="application/pdf"
        )

    # 5. JSON Findings Export
    with st.expander("🤖 Structured Payload & Database Run Export (JSON)", expanded=False):
        st.caption("Machine-readable payload stored in PostgreSQL and delivered to Gemini.")
        json_export = json.dumps(st.session_state.pipeline_result.to_serializable_dict(), indent=2)
        st.code(json_export, language="json")
