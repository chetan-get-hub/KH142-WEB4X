"""
Live end-to-end multi-domain and persistence verification script for DC4X
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)

from ingestion.loader import load_dataset, inspect_excel_sheets
from profiling.profiler import profile_dataset
from cleaning.cleaner import clean_dataset
from analysis.statistics import analyze_statistics
from analysis.anomalies import detect_anomalies
from reports.report_generator import generate_non_ai_summary, build_table_summary
from visualization.automatic import generate_automatic_visualizations
from models.result_models import OverallPipelineResult
from services.backend_client import BackendClient

client = BackendClient()

domains_datasets = [
    ("Healthcare", "data/healthcare_sample.csv", None),
    ("Sales & Retail", "data/sales_sample.csv", None),
    ("Human Resources (HR)", "data/hr_sample.csv", None),
    ("Finance & Banking", "data/finance_sample.xlsx", "Transactions")
]

created_run_codes = []

print("==================================================")
print("STARTING LIVE MULTI-DOMAIN DC4X PIPELINE TEST")
print("==================================================")

for domain, rel_path, sheet in domains_datasets:
    file_path = os.path.abspath(rel_path)
    file_name = os.path.basename(file_path)
    print(f"\n---> Testing Domain: {domain} | File: {file_name} (Sheet: {sheet})")

    df, meta = load_dataset(file_path, file_name, sheet_name=sheet)
    print(f"     Ingested {len(df)} rows, {len(df.columns)} columns.")

    raw_profile = profile_dataset(df, meta["file_name"], meta["file_type"], meta["file_size_bytes"], domain=domain)
    cleaned_df, clean_rep = clean_dataset(df, raw_profile)
    cleaned_prof = profile_dataset(cleaned_df, meta["file_name"], meta["file_type"], meta["file_size_bytes"], domain=domain)
    anom_rep = detect_anomalies(cleaned_df, cleaned_prof)
    stats_rep = analyze_statistics(cleaned_df, cleaned_prof, anomaly_report=anom_rep, domain=domain)
    auto_charts = generate_automatic_visualizations(cleaned_df, cleaned_prof, stats_rep, domain=domain)
    table_sum = build_table_summary(sheet or file_name, cleaned_prof, clean_rep, stats_rep, anom_rep)
    det_sum = generate_non_ai_summary(domain, cleaned_prof, clean_rep, stats_rep, anom_rep, stats_rep.findings)

    pipeline_res = OverallPipelineResult(
        domain=domain,
        file_name=file_name,
        sheet_name=sheet,
        profile=cleaned_prof,
        cleaning_report=clean_rep,
        analysis_report=stats_rep,
        anomaly_report=anom_rep,
        automatic_charts=auto_charts,
        summary_text=det_sum,
        table_summaries=[table_sum],
        findings=stats_rep.findings
    )

    # Submit to backend & PostgreSQL
    sub_res = client.submit_analysis_run(pipeline_res.to_serializable_dict(), trigger_ai_summary=True)
    run_code = sub_res.get("run_code")
    ai_status = sub_res.get("ai_status")
    print(f"     Persistence Status: SUCCESS | Run Code: {run_code}")
    print(f"     AI Synthesis Status: {ai_status}")
    if sub_res.get("ai_summary"):
        print(f"     AI Narrative snippet: {sub_res['ai_summary'].get('overall_summary', '')[:120]}...")

    created_run_codes.append(run_code)

print("\n==================================================")
print("VERIFYING POSTGRESQL RUN HISTORY LISTING")
print("==================================================")
history = client.list_historical_runs(limit=20)
print(f"Total historical runs retrieved from PostgreSQL: {len(history)}")
for h in history[:5]:
    print(f"- Run: {h.get('run_code')} | Domain: {h.get('domain')} | Dataset: {h.get('file_name')} | Findings: {h.get('findings_count')} | AI: {h.get('ai_status')}")

# Verify each created run exists in history
for rc in created_run_codes:
    det = client.get_historical_run(rc)
    assert det is not None, f"Failed to retrieve run {rc} from PostgreSQL"
    print(f"[OK] Verified Run {rc} persisted with {len(det.get('findings', []))} findings.")

print("\nALL 4 DOMAINS AND PERSISTENCE RETRIEVAL VERIFIED SUCCESSFULLY!")
