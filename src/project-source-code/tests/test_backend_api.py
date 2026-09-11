import pytest
import os
import sys
from fastapi.testclient import TestClient

from api.main import app
from db.database import init_db, check_db_connection, SessionLocal
from db.models import User, DatasetRun, FindingRecord, SummaryRecord

client = TestClient(app)

def test_fastapi_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database_connected" in data
    assert "gemini_configured" in data
    assert "gemini_model" in data

def test_database_initialization_and_models():
    init_success = init_db()
    assert init_success is True

    is_connected, msg = check_db_connection()
    assert is_connected is True

    # Test SessionLocal CRUD
    db = SessionLocal()
    try:
        # Create test user
        test_user = User(username="test_analyst@datacleaning4u.io", email="test_analyst@datacleaning4u.io")
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        assert test_user.id is not None

        # Create test run
        test_run = DatasetRun(
            user_id=test_user.id,
            file_name="test_sales.csv",
            file_type="CSV",
            domain="Sales & Retail",
            row_count=10,
            column_count=5,
            data_quality_score=95.0
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)
        assert test_run.id is not None

        # Create finding
        test_finding = FindingRecord(
            run_id=test_run.id,
            finding_id="FND_TEST_001",
            finding_type="TREND",
            title="Test Sales Surge",
            severity="High",
            confidence=0.95,
            category="Temporal",
            description="Test sales increase by 40%",
            evidence="Math: +40%"
        )
        db.add(test_finding)

        # Create summary
        test_sum = SummaryRecord(
            run_id=test_run.id,
            summary_type="DETERMINISTIC",
            content="Test deterministic summary",
            model_name="DataCleaning4U-Engine"
        )
        db.add(test_sum)
        db.commit()

        # Query back
        queried_run = db.query(DatasetRun).filter(DatasetRun.id == test_run.id).first()
        assert queried_run is not None
        assert len(queried_run.findings) == 1
        assert len(queried_run.summaries) == 1

        # Clean up test records
        db.delete(test_user)
        db.commit()

    finally:
        db.close()

def test_create_and_get_analysis_run_endpoint():
    sample_payload = {
        "domain": "Healthcare",
        "file_name": "healthcare_test.csv",
        "sheet_name": None,
        "username": "api_test@datacleaning4u.io",
        "trigger_ai_summary": False,  # No external API call in unit test
        "dataset_overview": {
            "total_rows": 20,
            "total_columns": 6,
            "numerical_columns": ["TreatmentCost", "SystolicBP"],
            "categorical_columns": ["Department"],
            "datetime_columns": ["AdmissionDate"],
            "identifier_columns": ["PatientID"]
        },
        "cleaning_metrics": {
            "rows_before": 20,
            "rows_after": 20,
            "duplicates_removed": 0,
            "total_missing_handled": 2,
            "conversions": {"AdmissionDate": "object -> datetime64"},
            "warnings": []
        },
        "statistical_summary": {
            "numerical": {"TreatmentCost": {"mean": 4500.0, "median": 4200.0}},
            "categorical": {"Department": {"unique_count": 3}},
            "group_aggregations": {"grouped_by": "Department", "target_metric": "TreatmentCost"},
            "correlations": {},
            "trends": {}
        },
        "anomaly_summary": {
            "total_anomalies": 1,
            "data_quality_issues": [],
            "method_counts": {"IQR": 1},
            "top_anomalies": []
        },
        "structured_findings": [
            {
                "id": "FND_CMP_001",
                "type": "COMPARISON",
                "title": "Cardiology Treatment Cost Disparity",
                "description": "Cardiology treatment cost is 45% above average",
                "severity": "High",
                "source_columns": ["Department", "TreatmentCost"],
                "supporting_values": {"top_mean": 6500.0},
                "confidence": 0.95,
                "category": "Performance",
                "evidence": "6500 vs 4500 mean"
            }
        ],
        "executive_summary_text": "Sample healthcare executive summary."
    }

    # POST run
    post_resp = client.post("/api/v1/analysis/runs", json=sample_payload)
    assert post_resp.status_code == 201
    res_data = post_resp.json()
    assert res_data["status"] == "COMPLETED"
    assert res_data["findings_count"] == 1
    assert res_data["file_name"] == "healthcare_test.csv"
    run_id = res_data["run_id"]

    # GET run
    get_resp = client.get(f"/api/v1/analysis/runs/{run_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["run_id"] == run_id
    assert get_data["domain"] == "Healthcare"

    # GET list
    list_resp = client.get("/api/v1/analysis/runs")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert len(list_data) >= 1
