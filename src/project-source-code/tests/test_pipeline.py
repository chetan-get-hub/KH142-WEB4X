import pytest
import os
import pandas as pd
import numpy as np
from ingestion.loader import load_dataset, inspect_excel_sheets, DatasetIngestionError
from profiling.profiler import profile_dataset
from cleaning.cleaner import clean_dataset
from analysis.statistics import analyze_statistics
from analysis.anomalies import detect_anomalies
from visualization.automatic import generate_automatic_visualizations
from visualization.user_selected import build_custom_visualization, ChartValidationError
from reports.report_generator import generate_non_ai_summary, generate_html_report, generate_pdf_report_bytes
from models.result_models import OverallPipelineResult

def test_csv_ingestion_and_pipeline():
    sample_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "sales_sample.csv"))
    assert os.path.exists(sample_csv_path)

    # 1. Ingestion
    df, meta = load_dataset(sample_csv_path, "sales_sample.csv")
    assert meta["total_rows"] > 0
    assert "SalesAmount" in df.columns

    # 2. Profiling
    profile = profile_dataset(df, meta["file_name"], meta["file_type"], meta["file_size_bytes"])
    assert profile.total_rows == len(df)
    assert len(profile.columns) == len(df.columns)

    # 3. Cleaning
    cleaned_df, clean_report = clean_dataset(df, profile)
    assert clean_report.rows_after <= clean_report.rows_before
    assert clean_report.duplicates_removed >= 1  # sales_sample contains duplicate TX1002

    # 4. Statistics
    analysis = analyze_statistics(cleaned_df, profile)
    assert len(analysis.numerical_summary) > 0

    # 5. Anomalies
    anomaly_rep = detect_anomalies(cleaned_df, profile)
    assert anomaly_rep.total_anomalies_found >= 0

    # 6. Automatic Visualizations
    auto_charts = generate_automatic_visualizations(cleaned_df, profile, analysis)
    assert len(auto_charts) >= 1

    # 7. User-Selected Visualization
    custom_chart = build_custom_visualization(
        cleaned_df, profile,
        chart_type="Bar Chart",
        x_col="Category",
        y_col="SalesAmount"
    )
    assert custom_chart.chart_type == "Bar Chart"

    # Test invalid chart selection validation
    with pytest.raises(ChartValidationError):
        build_custom_visualization(
            cleaned_df, profile,
            chart_type="Scatter Plot",
            x_col="Category",  # Categorical instead of numerical
            y_col="SalesAmount"
        )

    # 8. Report Generation
    summary_text = generate_non_ai_summary("Sales & Retail", profile, clean_report, analysis, anomaly_rep)
    assert "Sales & Retail" in summary_text

    pipeline_result = OverallPipelineResult(
        domain="Sales & Retail",
        file_name="sales_sample.csv",
        sheet_name=None,
        profile=profile,
        cleaning_report=clean_report,
        analysis_report=analysis,
        anomaly_report=anomaly_rep,
        automatic_charts=auto_charts,
        summary_text=summary_text
    )

    html_rep = generate_html_report(pipeline_result)
    assert "<html" in html_rep.lower()

    pdf_bytes = generate_pdf_report_bytes(pipeline_result)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

def test_excel_multi_sheet_ingestion():
    excel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "finance_sample.xlsx"))
    assert os.path.exists(excel_path)

    sheets = inspect_excel_sheets(excel_path)
    assert len(sheets) >= 2
    assert "Transactions" in sheets
    assert "AccountSummary" in sheets

    df_tx, meta_tx = load_dataset(excel_path, "finance_sample.xlsx", sheet_name="Transactions")
    assert meta_tx["sheet_name"] == "Transactions"
    assert "Amount" in df_tx.columns

    df_acc, meta_acc = load_dataset(excel_path, "finance_sample.xlsx", sheet_name="AccountSummary")
    assert meta_acc["sheet_name"] == "AccountSummary"
    assert "CurrentBalance" in df_acc.columns
