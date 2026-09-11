import pytest
import os
import io
import json
import pandas as pd
import numpy as np

from ingestion.loader import load_dataset, inspect_excel_sheets, DatasetIngestionError
from profiling.profiler import profile_dataset
from cleaning.cleaner import clean_dataset
from analysis.statistics import analyze_statistics
from analysis.anomalies import detect_anomalies
from analysis.findings import detect_structured_findings
from visualization.automatic import generate_automatic_visualizations
from visualization.user_selected import build_custom_visualization, ChartValidationError
from reports.report_generator import (
    generate_non_ai_summary,
    generate_html_report,
    generate_pdf_report_bytes,
    build_table_summary
)
from models.result_models import OverallPipelineResult, Finding

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))

def test_csv_ingestion_and_pipeline():
    sample_csv_path = os.path.join(DATA_DIR, "sales_sample.csv")
    assert os.path.exists(sample_csv_path)

    # 1. Ingestion
    df, meta = load_dataset(sample_csv_path, "sales_sample.csv")
    assert meta["total_rows"] > 0
    assert "SalesAmount" in df.columns

    # 2. Profiling with domain context
    profile = profile_dataset(df, meta["file_name"], meta["file_type"], meta["file_size_bytes"], domain="Sales & Retail")
    assert profile.total_rows == len(df)
    assert len(profile.columns) == len(df.columns)
    assert profile.columns["SalesAmount"].suitable_for_measurement is True
    assert profile.columns["Region"].suitable_for_grouping is True

    # 3. Cleaning
    cleaned_df, clean_report = clean_dataset(df, profile)
    assert clean_report.rows_after <= clean_report.rows_before
    assert clean_report.duplicates_removed >= 1  # sales_sample contains duplicate TX1002

    # 4. Profiling Cleaned Data
    cleaned_profile = profile_dataset(cleaned_df, meta["file_name"], meta["file_type"], meta["file_size_bytes"], domain="Sales & Retail")

    # 5. Anomaly Detection
    anomaly_rep = detect_anomalies(cleaned_df, cleaned_profile)
    assert anomaly_rep.total_anomalies_found >= 0

    # 6. Statistics & Finding Generation
    analysis = analyze_statistics(cleaned_df, cleaned_profile, anomaly_report=anomaly_rep, domain="Sales & Retail")
    assert len(analysis.numerical_summary) > 0
    assert len(analysis.findings) > 0

    # Verify structured finding properties
    for f in analysis.findings:
        assert isinstance(f, Finding)
        assert f.id.startswith("FND_")
        assert f.type in ["TREND", "COMPARISON", "CORRELATION", "DOMINANT_CATEGORY", "ANOMALY", "DATA_QUALITY", "DISTRIBUTION", "SIGNIFICANT_CHANGE"]
        assert len(f.evidence) > 0
        assert 0.0 <= f.confidence <= 1.0

    # 7. Automatic Visualizations
    auto_charts = generate_automatic_visualizations(cleaned_df, cleaned_profile, analysis, domain="Sales & Retail")
    assert len(auto_charts) >= 1
    assert auto_charts[0].plotly_json is not None
    assert len(auto_charts[0].reason) > 0

    # 8. User-Selected Visualization
    custom_chart = build_custom_visualization(
        cleaned_df, cleaned_profile,
        chart_type="Bar Chart",
        x_col="Category",
        y_col="SalesAmount"
    )
    assert custom_chart.chart_type.lower() in ["bar chart", "bar"]

    # Test invalid chart selection validation
    with pytest.raises(ChartValidationError):
        build_custom_visualization(
            cleaned_df, cleaned_profile,
            chart_type="Scatter Plot",
            x_col="Category",  # Categorical instead of numerical
            y_col="SalesAmount"
        )

    # 9. Table Summary & Executive Summary
    table_sum = build_table_summary("sales_sample.csv", cleaned_profile, clean_report, analysis, anomaly_rep)
    assert table_sum.data_quality_score > 0
    assert len(table_sum.top_findings) > 0

    summary_text = generate_non_ai_summary("Sales & Retail", cleaned_profile, clean_report, analysis, anomaly_rep, analysis.findings)
    assert "Sales & Retail" in summary_text
    assert "Data Hygiene" in summary_text

    pipeline_result = OverallPipelineResult(
        domain="Sales & Retail",
        file_name="sales_sample.csv",
        sheet_name=None,
        profile=cleaned_profile,
        cleaning_report=clean_report,
        analysis_report=analysis,
        anomaly_report=anomaly_rep,
        automatic_charts=auto_charts,
        summary_text=summary_text,
        table_summaries=[table_sum],
        findings=analysis.findings
    )

    # 10. Report Exports
    html_rep = generate_html_report(pipeline_result)
    assert "<html" in html_rep.lower()
    assert "DC4X" in html_rep

    pdf_bytes = generate_pdf_report_bytes(pipeline_result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

    # 11. Serialization test for future AI API
    serializable = pipeline_result.to_serializable_dict()
    assert isinstance(serializable, dict)
    json_str = json.dumps(serializable)
    assert len(json_str) > 0
    assert "structured_findings" in serializable


def test_excel_multi_sheet_ingestion():
    excel_path = os.path.join(DATA_DIR, "finance_sample.xlsx")
    assert os.path.exists(excel_path)

    sheets = inspect_excel_sheets(excel_path)
    assert len(sheets) >= 2
    assert "Transactions" in sheets
    assert "AccountSummary" in sheets

    # Sheet 1: Transactions
    df_tx, meta_tx = load_dataset(excel_path, "finance_sample.xlsx", sheet_name="Transactions")
    prof_tx = profile_dataset(df_tx, "finance_sample.xlsx", "XLSX", domain="Finance & Banking")
    clean_tx, rep_tx = clean_dataset(df_tx, prof_tx)
    anom_tx = detect_anomalies(clean_tx, prof_tx)
    stat_tx = analyze_statistics(clean_tx, prof_tx, anomaly_report=anom_tx, domain="Finance & Banking")

    assert "Amount" in clean_tx.columns
    assert stat_tx.numerical_summary["Amount"]["mean"] > 0

    # Sheet 2: AccountSummary
    df_acc, meta_acc = load_dataset(excel_path, "finance_sample.xlsx", sheet_name="AccountSummary")
    prof_acc = profile_dataset(df_acc, "finance_sample.xlsx", "XLSX", domain="Finance & Banking")
    clean_acc, rep_acc = clean_dataset(df_acc, prof_acc)
    anom_acc = detect_anomalies(clean_acc, prof_acc)
    stat_acc = analyze_statistics(clean_acc, prof_acc, anomaly_report=anom_acc, domain="Finance & Banking")

    assert "CurrentBalance" in clean_acc.columns
    assert "CreditScore" in clean_acc.columns


def test_healthcare_domain_and_findings():
    sample_path = os.path.join(DATA_DIR, "healthcare_sample.csv")
    assert os.path.exists(sample_path)

    df, meta = load_dataset(sample_path, "healthcare_sample.csv")
    profile = profile_dataset(df, "healthcare_sample.csv", "CSV", domain="Healthcare")
    cleaned_df, clean_rep = clean_dataset(df, profile)
    cleaned_profile = profile_dataset(cleaned_df, "healthcare_sample.csv", "CSV", domain="Healthcare")

    anom_rep = detect_anomalies(cleaned_df, cleaned_profile)
    analysis = analyze_statistics(cleaned_df, cleaned_profile, anomaly_report=anom_rep, domain="Healthcare")

    assert "SystolicBP" in cleaned_profile.numerical_columns
    assert "Department" in cleaned_profile.categorical_columns
    assert len(analysis.findings) > 0


def test_hr_domain_and_findings():
    sample_path = os.path.join(DATA_DIR, "hr_sample.csv")
    assert os.path.exists(sample_path)

    df, meta = load_dataset(sample_path, "hr_sample.csv")
    profile = profile_dataset(df, "hr_sample.csv", "CSV", domain="Human Resources (HR)")
    cleaned_df, clean_rep = clean_dataset(df, profile)
    cleaned_profile = profile_dataset(cleaned_df, "hr_sample.csv", "CSV", domain="Human Resources (HR)")

    anom_rep = detect_anomalies(cleaned_df, cleaned_profile)
    analysis = analyze_statistics(cleaned_df, cleaned_profile, anomaly_report=anom_rep, domain="Human Resources (HR)")

    assert "Salary" in cleaned_profile.numerical_columns
    assert len(analysis.findings) > 0


def test_edge_case_datasets():
    # 1. Single numerical column dataset
    df_single = pd.DataFrame({"MetricOnly": [10.0, 20.0, 30.0, 40.0, 50.0]})
    prof_single = profile_dataset(df_single, "single.csv", "CSV")
    clean_single, _ = clean_dataset(df_single, prof_single)
    anom_single = detect_anomalies(clean_single, prof_single)
    stat_single = analyze_statistics(clean_single, prof_single, anomaly_report=anom_single)
    charts_single = generate_automatic_visualizations(clean_single, prof_single, stat_single)
    assert len(stat_single.numerical_summary) == 1
    assert len(charts_single) >= 1

    # 2. All text categorical dataset
    df_text = pd.DataFrame({"Category": ["A", "B", "A", "C", "A"], "Status": ["Active", "Active", "Pending", "Active", "Pending"]})
    prof_text = profile_dataset(df_text, "text.csv", "CSV")
    clean_text, _ = clean_dataset(df_text, prof_text)
    anom_text = detect_anomalies(clean_text, prof_text)
    stat_text = analyze_statistics(clean_text, prof_text, anomaly_report=anom_text)
    assert len(stat_text.categorical_summary) == 2

    # 3. Constant column / zero variance
    df_const = pd.DataFrame({"ConstantCol": [100, 100, 100, 100], "Varying": [1, 2, 3, 4]})
    prof_const = profile_dataset(df_const, "const.csv", "CSV")
    anom_const = detect_anomalies(df_const, prof_const)
    assert any(dq["issue_type"] == "Zero Variance / Constant" for dq in anom_const.data_quality_issues)

    # 4. Column with all NaNs
    df_nan = pd.DataFrame({"GoodCol": [1, 2, 3, 4], "AllNaN": [np.nan, np.nan, np.nan, np.nan]})
    prof_nan = profile_dataset(df_nan, "nan.csv", "CSV")
    clean_nan, rep_nan = clean_dataset(df_nan, prof_nan)
    assert clean_nan is not None
