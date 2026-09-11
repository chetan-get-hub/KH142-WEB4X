"""
Tests for DC4X Run History Persistence and Retrieval
"""
import pytest
from services.backend_client import BackendClient
from db.database import SessionLocal, init_db
from db.models import User, DatasetRun, FindingRecord, SummaryRecord

def test_run_history_persistence_and_retrieval():
    init_db()
    client = BackendClient()

    # Ingest mock run
    mock_pipeline = {
        "domain": "Finance & Banking",
        "file_name": "test_finance.xlsx",
        "sheet_name": "Transactions",
        "dataset_overview": {"total_rows": 50, "total_columns": 5},
        "cleaning_metrics": {"rows_after": 50, "duplicates_removed": 1},
        "statistical_summary": {"numerical": {"balance": {"mean": 25000.0}}},
        "anomaly_summary": {"total_anomalies": 2},
        "structured_findings": [
            {
                "id": "FND_FIN_001",
                "type": "ANOMALY",
                "title": "High Value Transaction Spike",
                "severity": "High",
                "confidence": 0.98,
                "category": "Risk",
                "description": "Single debit exceeding $100,000.",
                "evidence": "Observed 105,000 vs 25,000 mean."
            }
        ],
        "executive_summary_text": "Deterministic finance summary for testing."
    }

    sub_res = client.submit_analysis_run(mock_pipeline, trigger_ai_summary=False)
    assert sub_res is not None
    assert "run_id" in sub_res
    run_code = sub_res.get("run_code")
    assert run_code is not None

    # List historical runs
    history = client.list_historical_runs(limit=10)
    assert len(history) > 0
    matched = next((h for h in history if h.get("run_code") == run_code), None)
    assert matched is not None
    assert matched["domain"] == "Finance & Banking"
    assert matched["file_name"] == "test_finance.xlsx"

    # Retrieve detailed run
    detailed = client.get_historical_run(run_code)
    assert detailed is not None
    assert detailed["run_code"] == run_code
    assert len(detailed["findings"]) >= 1
    assert detailed["findings"][0]["title"] == "High Value Transaction Spike"
