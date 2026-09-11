import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path.cwd() / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from services.llm_service import GeminiService

service = GeminiService(model="gemini-3.6-flash")
print(f"Service is available: {service.is_available()}")

mock_payload = {
    "domain": "Healthcare",
    "file_name": "healthcare_sample.csv",
    "dataset_overview": {"row_count": 100, "column_count": 8},
    "cleaning_metrics": {"duplicates_removed": 2, "missing_cells_imputed": 5},
    "structured_findings": [
        {
            "finding_type": "statistical",
            "title": "Systolic BP Distribution Shift",
            "severity": "high",
            "description": "Systolic BP average is 142.5 mmHg with 12 patients in stage 2 hypertension.",
            "evidence": {"mean": 142.5, "hypertension_count": 12}
        }
    ],
    "anomaly_summary": {"total_anomalies": 3},
    "statistical_summary": {"numerical": {"systolicbp": {"mean": 142.5, "std": 15.2}}}
}

result = service.generate_narrative_explanation(mock_payload)
print(f"Result Status: {result.get('status')}")
print(f"Result Fallback Used: {result.get('fallback_used')}")
if result.get("ai_summary"):
    print("AI Summary Overall:", result["ai_summary"].get("overall_summary"))
    print("Key Findings:", result["ai_summary"].get("key_findings"))
