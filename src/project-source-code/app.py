import sys
import os
import io
import json
import streamlit as st
import pandas as pd
import plotly.io as pio

# Add project-source-code to sys.path for robust imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import SUPPORTED_DOMAINS, DOMAIN_TAGLINES
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
    generate_pdf_report_bytes
)
from models.result_models import OverallPipelineResult

# Page configuration
st.set_page_config(
    page_title="DataCleaning4U - Autonomous Data Analyst Agent",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Vanilla CSS)
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .tagline {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #4F46E5;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .step-header {
        background: #EEF2FF;
        color: #4F46E5;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #4F46E5;
    }
    .summary-box {
        background-color: #F1F5F9;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #10B981;
        font-size: 1.05rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "selected_domain" not in st.session_state:
    st.session_state.selected_domain = SUPPORTED_DOMAINS[0]
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None

# Header
col_header, col_user = st.columns([3, 1])
with col_header:
    st.markdown('<div class="main-title">DataCleaning4U</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">From raw data to useful insights</div>', unsafe_allow_html=True)

with col_user:
    if st.session_state.authenticated:
        st.write(f"👤 **Logged in as:** `{st.session_state.username}`")
        if st.button("Logout", key="btn_logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()

# Authentication Screen (Development Login)
if not st.session_state.authenticated:
    st.info("🔐 **DataCleaning4U Login** (Hackathon Demo Auth)")
    with st.form("login_form"):
        user_input = st.text_input("Username / Email", value="analyst@datacleaning4u.io")
        pass_input = st.text_input("Password", type="password", value="demo123")
        submitted = st.form_submit_button("Log In & Start Analysis")
        if submitted:
            if user_input:
                st.session_state.authenticated = True
                st.session_state.username = user_input
                st.success("Successfully logged in!")
                st.rerun()
            else:
                st.error("Please enter a username.")
    st.stop()

# Sidebar Setup
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    # 1. Domain Selector
    st.subheader("1. Select Domain")
    st.session_state.selected_domain = st.selectbox(
        "Choose analysis domain:",
        SUPPORTED_DOMAINS,
        index=SUPPORTED_DOMAINS.index(st.session_state.selected_domain)
    )
    st.caption(f"ℹ️ {DOMAIN_TAGLINES.get(st.session_state.selected_domain, '')}")
    st.markdown("---")

    # 2. File Upload / Sample Datasets
    st.subheader("2. Dataset Source")
    load_option = st.radio("Choose source:", ["Upload File", "Use Sample Dataset"])
    
    uploaded_file = None
    sample_file_path = None
    sheet_selected = None

    if load_option == "Upload File":
        uploaded_file = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx", "xls"])
        if uploaded_file and uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
            try:
                sheets = inspect_excel_sheets(uploaded_file)
                if len(sheets) > 1:
                    sheet_selected = st.selectbox("Select Excel Sheet:", sheets)
                else:
                    sheet_selected = sheets[0]
            except Exception as e:
                st.warning(f"Could not inspect sheets: {e}")

    else:
        sample_dict = {
            "Sales & Retail": "sales_sample.csv",
            "Finance & Banking": "finance_sample.xlsx",
            "Healthcare": "healthcare_sample.csv",
            "Human Resources (HR)": "hr_sample.csv"
        }
        chosen_sample = sample_dict.get(st.session_state.selected_domain, "sales_sample.csv")
        sample_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", chosen_sample))
        st.write(f"📁 Selected sample: `{chosen_sample}`")
        if chosen_sample.endswith('.xlsx'):
            try:
                sheets = inspect_excel_sheets(sample_file_path)
                if len(sheets) > 1:
                    sheet_selected = st.selectbox("Select Sheet:", sheets)
            except Exception:
                pass

    st.markdown("---")

# Main Content Tabs
tabs = st.tabs([
    "📥 Ingestion & Profiling",
    "🧹 Cleaning & Progress",
    "📊 Statistical Analysis",
    "⚠️ Anomaly Detection",
    "📈 Visualizations & Custom Builder",
    "📝 Executive Summary & Reports"
])

file_input = uploaded_file or sample_file_path

if not file_input:
    st.info("👈 Please select or upload a dataset using the sidebar control panel to begin analysis.")
    st.stop()

# Pipeline Execution
try:
    fname = uploaded_file.name if uploaded_file else os.path.basename(sample_file_path)
    raw_df, meta = load_dataset(file_input, fname, sheet_name=sheet_selected)
    
    # Save raw DF copy
    st.session_state.raw_df = raw_df

    # Profile raw dataset
    profile = profile_dataset(raw_df, meta["file_name"], meta["file_type"], meta["file_size_bytes"])
    
    # Clean dataset
    cleaned_df, cleaning_rep = clean_dataset(raw_df, profile)
    st.session_state.cleaned_df = cleaned_df

    # Profile cleaned dataset for stats
    cleaned_profile = profile_dataset(cleaned_df, meta["file_name"], meta["file_type"], meta["file_size_bytes"])

    # Analyze & Detect Anomalies
    analysis_rep = analyze_statistics(cleaned_df, cleaned_profile)
    anomaly_rep = detect_anomalies(cleaned_df, cleaned_profile)

    # Automatic charts
    auto_charts = generate_automatic_visualizations(cleaned_df, cleaned_profile, analysis_rep)

    # Summary
    summary_text = generate_non_ai_summary(
        st.session_state.selected_domain,
        cleaned_profile,
        cleaning_rep,
        analysis_rep,
        anomaly_rep
    )

    st.session_state.pipeline_result = OverallPipelineResult(
        domain=st.session_state.selected_domain,
        file_name=fname,
        sheet_name=sheet_selected,
        profile=cleaned_profile,
        cleaning_report=cleaning_rep,
        analysis_report=analysis_rep,
        anomaly_report=anomaly_rep,
        automatic_charts=auto_charts,
        summary_text=summary_text
    )

except DatasetIngestionError as die:
    st.error(f"❌ File Ingestion Error: {str(die)}")
    st.stop()
except Exception as ex:
    st.error(f"❌ Processing Error: {str(ex)}")
    st.stop()


# ----------------------------------------------------
# TAB 1: Ingestion & Profiling
# ----------------------------------------------------
with tabs[0]:
    st.markdown('<div class="step-header">📁 Dataset Profile & Overview</div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{profile.total_rows:,}</div><div class="metric-lbl">Total Rows</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{profile.total_columns}</div><div class="metric-lbl">Total Columns</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{profile.file_type}</div><div class="metric-lbl">File Type</div></div>', unsafe_allow_html=True)
    with c4:
        size_str = f"{profile.file_size_bytes / 1024:.1f} KB" if profile.file_size_bytes else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-val">{size_str}</div><div class="metric-lbl">File Size</div></div>', unsafe_allow_html=True)

    st.subheader("Raw Data Preview (First 5 Rows)")
    st.dataframe(raw_df.head(5), use_container_width=True)

    st.subheader("Column Taxonomy & Data Types")
    col_summary_data = []
    for col, p in profile.columns.items():
        col_summary_data.append({
            "Column Name": col,
            "Inferred Type": p.inferred_type.upper(),
            "Raw Dtype": p.raw_dtype,
            "Missing Count": f"{p.missing_count} ({p.missing_percentage}%)",
            "Unique Count": p.unique_count,
            "Sample Values": ", ".join(map(str, p.sample_values[:3]))
        })
    st.dataframe(pd.DataFrame(col_summary_data), use_container_width=True)


# ----------------------------------------------------
# TAB 2: Cleaning & Progress
# ----------------------------------------------------
with tabs[2-1]:
    st.markdown('<div class="step-header">🧹 Data Cleaning Progress & Report</div>', unsafe_allow_html=True)

    st.subheader("Step-by-Step Processing Pipeline")
    for step in cleaning_rep.cleaning_steps:
        with st.expander(f"✅ Step: {step['step']}", expanded=True):
            for detail in step["details"]:
                st.write(f"- {detail}")

    st.subheader("Before vs. After Cleaning Metrics")
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.metric("Rows Count", f"{cleaning_rep.rows_after:,}", delta=f"-{cleaning_rep.duplicates_removed} duplicates")
    with b2:
        st.metric("Missing Values Handled", f"{cleaning_rep.total_missing_handled}")
    with b3:
        st.metric("Datatypes Converted", f"{len(cleaning_rep.datatype_conversions)}")
    with b4:
        st.metric("Outliers Flagged", f"{cleaning_rep.outliers_flagged_count}")

    if cleaning_rep.warnings:
        st.warning("⚠️ Data Quality Warnings:\n" + "\n".join([f"- {w}" for w in cleaning_rep.warnings]))

    st.subheader("Cleaned Dataset Preview")
    st.dataframe(cleaned_df.head(10), use_container_width=True)


# ----------------------------------------------------
# TAB 3: Statistical Analysis
# ----------------------------------------------------
with tabs[2]:
    st.markdown('<div class="step-header">📊 Statistical Engine Findings</div>', unsafe_allow_html=True)
    
    st.subheader("1. Numerical Column Statistics")
    if analysis_rep.numerical_summary:
        st.dataframe(pd.DataFrame(analysis_rep.numerical_summary).T, use_container_width=True)
    else:
        st.info("No numerical columns available for analysis.")

    st.subheader("2. Categorical Column Summaries")
    if analysis_rep.categorical_summary:
        st.dataframe(pd.DataFrame(analysis_rep.categorical_summary).T, use_container_width=True)
    else:
        st.info("No categorical columns available.")

    st.subheader("3. Group Aggregation Insights")
    if analysis_rep.group_aggregations:
        grp = analysis_rep.group_aggregations
        st.write(f"Aggregating metric **'{grp['target_metric']}'** grouped by **'{grp['grouped_by']}'**:")
        if "group_table" in grp:
            st.dataframe(pd.DataFrame(grp["group_table"]), use_container_width=True)


# ----------------------------------------------------
# TAB 4: Anomaly Detection
# ----------------------------------------------------
with tabs[3]:
    st.markdown('<div class="step-header">⚠️ Anomaly & Outlier Audit</div>', unsafe_allow_html=True)

    a1, a2 = st.columns(2)
    with a1:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{len(anomaly_rep.data_quality_issues)}</div><div class="metric-lbl">Data Quality Defects</div></div>', unsafe_allow_html=True)
    with a2:
        st.markdown(f'<div class="metric-card"><div class="metric-val">{anomaly_rep.total_anomalies_found}</div><div class="metric-lbl">Statistical Anomalies</div></div>', unsafe_allow_html=True)

    st.subheader("Data Quality Defects")
    if anomaly_rep.data_quality_issues:
        st.dataframe(pd.DataFrame(anomaly_rep.data_quality_issues), use_container_width=True)
    else:
        st.success("No critical data quality defects detected.")

    st.subheader("Statistical Outliers (IQR / Z-Score / Isolation Forest)")
    if anomaly_rep.statistical_anomalies:
        anom_table = []
        for item in anomaly_rep.statistical_anomalies[:25]:
            anom_table.append({
                "Column": item.column,
                "Row Index": item.row_index,
                "Observed Value": item.value,
                "Severity Score": item.score,
                "Method": item.method,
                "Explanation": item.explanation
            })
        st.dataframe(pd.DataFrame(anom_table), use_container_width=True)
    else:
        st.success("No extreme statistical outliers detected.")


# ----------------------------------------------------
# TAB 5: Visualizations & Custom Builder
# ----------------------------------------------------
with tabs[4]:
    st.markdown('<div class="step-header">📈 Automatically Generated Visualizations</div>', unsafe_allow_html=True)
    
    if auto_charts:
        for chart_res in auto_charts:
            st.subheader(chart_res.title)
            st.caption(chart_res.description)
            fig_obj = pio.from_json(chart_res.plotly_json)
            st.plotly_chart(fig_obj, use_container_width=True)
    else:
        st.info("No automatic charts could be generated for this dataset.")

    st.markdown("---")
    st.markdown('<div class="step-header">🎨 Interactive Custom Visualization Builder</div>', unsafe_allow_html=True)
    
    c_type, c_x, c_y, c_grp = st.columns(4)
    with c_type:
        chart_choice = st.selectbox("Chart Type:", ["Bar Chart", "Line Chart", "Scatter Plot", "Histogram", "Box Plot", "Pie Chart", "Heatmap"])
    with c_x:
        x_choice = st.selectbox("X Axis Column:", ["None"] + list(cleaned_df.columns))
    with c_y:
        y_choice = st.selectbox("Y Axis Column:", ["None"] + list(cleaned_df.columns))
    with c_grp:
        grp_choice = st.selectbox("Group / Color By (Optional):", ["None"] + list(cleaned_df.columns))

    if st.button("Generate Custom Chart", type="primary"):
        try:
            custom_res = build_custom_visualization(
                cleaned_df,
                cleaned_profile,
                chart_type=chart_choice,
                x_col=x_choice if x_choice != "None" else None,
                y_col=y_choice if y_choice != "None" else None,
                group_col=grp_choice if grp_choice != "None" else None
            )
            st.success(f"Generated custom {chart_choice} successfully!")
            fig_custom = pio.from_json(custom_res.plotly_json)
            st.plotly_chart(fig_custom, use_container_width=True)
        except ChartValidationError as cve:
            st.error(f"⚠️ Validation Warning: {str(cve)}")
        except Exception as ex:
            st.error(f"❌ Chart Generation Error: {str(ex)}")


# ----------------------------------------------------
# TAB 6: Executive Summary & Reports
# ----------------------------------------------------
with tabs[5]:
    st.markdown('<div class="step-header">📝 Executive Natural-Language Summary (Non-AI)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-box">{summary_text.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="step-header">📥 Export & Download Center</div>', unsafe_allow_html=True)

    d1, d2, d3, d4 = st.columns(4)

    # 1. Cleaned CSV
    csv_bytes = cleaned_df.to_csv(index=False).encode('utf-8')
    with d1:
        st.download_button(
            label="📄 Download Cleaned CSV",
            data=csv_bytes,
            file_name=f"cleaned_{fname}.csv",
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
            file_name=f"cleaned_{fname}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 3. HTML Audit Report
    html_report_str = generate_html_report(st.session_state.pipeline_result)
    with d3:
        st.download_button(
            label="🌐 Download HTML Report",
            data=html_report_str.encode('utf-8'),
            file_name=f"report_{fname}.html",
            mime="text/html"
        )

    # 4. PDF Audit Report
    pdf_report_bytes = generate_pdf_report_bytes(st.session_state.pipeline_result)
    with d4:
        st.download_button(
            label="📕 Download PDF Report",
            data=pdf_report_bytes,
            file_name=f"report_{fname}.pdf",
            mime="application/pdf"
        )
