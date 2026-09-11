import pytest
import pandas as pd
import plotly.express as px
from models.result_models import (
    OverallPipelineResult,
    DatasetProfile,
    CleaningReport,
    AnalysisReport,
    AnomalyReport,
    VisualizationResult,
    Finding
)
from profiling.profiler import profile_dataset
from cleaning.cleaner import clean_dataset
from analysis.statistics import analyze_statistics
from analysis.anomalies import detect_anomalies
from visualization.automatic import generate_automatic_visualizations, apply_chart_theme
from reports.report_generator import generate_non_ai_summary, build_table_summary

def test_overall_pipeline_result_contract_compatibility():
    """Verify OverallPipelineResult accepts both visualizations/automatic_charts and summary_text/overall_summary without error."""
    prof = DatasetProfile(
        total_rows=10,
        total_columns=2,
        file_name="test.csv",
        file_type="csv",
        file_size_bytes=100,
        columns={},
        numerical_columns=["a", "b"],
        categorical_columns=[],
        datetime_columns=[],
        boolean_columns=[],
        identifier_columns=[]
    )
    clean = CleaningReport(
        rows_before=10,
        rows_after=10,
        cols_before=2,
        cols_after=2,
        duplicates_found=0,
        duplicates_removed=0,
        missing_handled_per_column={},
        total_missing_handled=0,
        datatype_conversions={},
        standardized_columns=[],
        outliers_flagged_count=0,
        warnings=[],
        cleaning_steps=[]
    )
    stats = AnalysisReport(
        numerical_summary={},
        categorical_summary={},
        group_aggregations={},
        correlations={},
        trends={},
        findings=[]
    )
    anom = AnomalyReport(
        total_anomalies_found=0,
        data_quality_issues=[],
        statistical_anomalies=[],
        method_summaries={}
    )
    viz = [VisualizationResult(
        chart_id="CHART_01",
        title="Test Chart",
        chart_type="bar",
        plotly_json="{}",
        description="Test Desc"
    )]
    finding = Finding(
        id="F01",
        type="TREND",
        title="Test Finding",
        description="Test Obs",
        severity="Medium",
        source_columns=["a"],
        supporting_values={"metric": 1},
        confidence=0.9,
        category="General",
        evidence="Evidence text"
    )

    # 1. Instantiation with 'visualizations' and 'summary_text' (Old/Streamlit convention)
    res1 = OverallPipelineResult(
        domain="Sales & Retail",
        file_name="test.csv",
        sheet_name=None,
        profile=prof,
        cleaning_report=clean,
        analysis_report=stats,
        anomaly_report=anom,
        findings=[finding],
        visualizations=viz,
        summary_text="Deterministic test summary"
    )

    assert len(res1.visualizations) == 1
    assert len(res1.automatic_charts) == 1
    assert res1.summary_text == "Deterministic test summary"
    assert res1.overall_summary == "Deterministic test summary"

    # 2. Instantiation with 'automatic_charts' and 'overall_summary' (Original dataclass convention)
    res2 = OverallPipelineResult(
        domain="Sales & Retail",
        file_name="test.csv",
        sheet_name=None,
        profile=prof,
        cleaning_report=clean,
        analysis_report=stats,
        anomaly_report=anom,
        findings=[finding],
        automatic_charts=viz,
        overall_summary="Deterministic test summary 2"
    )

    assert len(res2.visualizations) == 1
    assert len(res2.automatic_charts) == 1
    assert res2.summary_text == "Deterministic test summary 2"
    assert res2.overall_summary == "Deterministic test summary 2"

    # 3. Serialization
    d1 = res1.to_serializable_dict()
    assert d1["domain"] == "Sales & Retail"
    assert d1["dataset_overview"]["total_rows"] == 10
    assert d1["executive_summary_text"] == "Deterministic test summary"

def test_chart_theming_dark_and_light_mode():
    """Verify that apply_chart_theme correctly sets color schemes and layout for dark neon and clean light themes."""
    df = pd.DataFrame({"x": ["A", "B", "C"], "y": [10, 20, 15]})
    fig = px.bar(df, x="x", y="y")

    # Dark Neon Mode
    dark_fig = apply_chart_theme(fig, "Dark Mode Chart", theme_mode="dark")
    assert dark_fig.layout.paper_bgcolor == "#14141A"
    assert dark_fig.layout.plot_bgcolor == "#181822"
    assert dark_fig.layout.font.color == "#F5EEDB"
    assert dark_fig.layout.title.text == "<b>Dark Mode Chart</b>"

    # Clean Light Mode
    light_fig = apply_chart_theme(fig, "Light Mode Chart", theme_mode="light")
    assert light_fig.layout.paper_bgcolor == "#FFFFFF"
    assert light_fig.layout.plot_bgcolor == "#F8FAFC"
    assert light_fig.layout.font.color == "#0F172A"
    assert light_fig.layout.title.text == "<b>Light Mode Chart</b>"

def test_pipeline_end_to_end_result_creation():
    """Verify that the full pipeline executes and returns a robust OverallPipelineResult with visualizations attached."""
    df = pd.DataFrame({
        "Patient_ID": [101, 102, 103, 104, 105],
        "Age": [45, 52, 60, 34, 71],
        "Blood_Pressure": [120, 135, 140, 118, 160],
        "Condition": ["Normal", "Prehypertension", "Stage 1", "Normal", "Stage 2"]
    })

    profile = profile_dataset(df, "healthcare_test.csv", "csv", 500, domain="Healthcare & Medical")
    cleaned_df, clean_report = clean_dataset(df, profile)
    cleaned_profile = profile_dataset(cleaned_df, "healthcare_test.csv", "csv", 500, domain="Healthcare & Medical")
    anomaly_rep = detect_anomalies(cleaned_df, cleaned_profile)
    analysis = analyze_statistics(cleaned_df, cleaned_profile, anomaly_report=anomaly_rep, domain="Healthcare & Medical")
    charts = generate_automatic_visualizations(cleaned_df, cleaned_profile, analysis, theme_mode="light")
    summary = generate_non_ai_summary("Healthcare & Medical", cleaned_profile, clean_report, analysis, anomaly_rep, analysis.findings)
    tbl_summary = build_table_summary("healthcare_test.csv", cleaned_profile, clean_report, analysis, anomaly_rep)

    result = OverallPipelineResult(
        domain="Healthcare & Medical",
        file_name="healthcare_test.csv",
        sheet_name=None,
        profile=cleaned_profile,
        cleaning_report=clean_report,
        analysis_report=analysis,
        anomaly_report=anomaly_rep,
        findings=analysis.findings,
        visualizations=charts,
        summary_text=summary,
        table_summaries=[tbl_summary]
    )

    assert isinstance(result, OverallPipelineResult)
    assert result.file_name == "healthcare_test.csv"
    assert result.domain == "Healthcare & Medical"
    assert result.profile.total_rows == 5
    assert len(result.findings) >= 1
    assert len(result.automatic_charts) >= 1
    assert result.summary_text is not None
    assert len(result.summary_text) > 0
