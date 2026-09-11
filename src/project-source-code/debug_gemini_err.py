import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)

from services.llm_service import GeminiService

svc = GeminiService()
print(f"API Key present: {svc.is_available()}, Model: {svc.model}")

mock_payload = {
    "domain": "Healthcare",
    "file_name": "healthcare_sample.csv",
    "dataset_overview": {"total_rows": 100, "total_columns": 8},
    "cleaning_metrics": {"duplicates_removed": 2, "missing_cells_imputed": 5},
    "structured_findings": [
        {
            "id": "FND_001",
            "type": "statistical",
            "title": "Systolic BP Distribution Shift",
            "severity": "high",
            "description": "Systolic BP average is 142.5 mmHg with 12 patients in stage 2 hypertension.",
            "evidence": "mean 142.5"
        }
    ],
    "anomaly_summary": {"total_anomalies": 3},
    "statistical_summary": {"numerical": {"systolicbp": {"mean": 142.5, "std": 15.2}}}
}

res = svc.generate_narrative_explanation(mock_payload)
print(f"Status: {res['status']}")
print(f"Message: {res['message']}")
if res.get("ai_summary"):
    print(f"Overall summary: {res['ai_summary'].get('overall_summary')}")
