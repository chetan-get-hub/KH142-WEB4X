import pytest
import json
from unittest.mock import MagicMock, patch
from services.llm_service import GeminiService, AISummaryResponse, TableSummaryItem, AnomalyExplanationItem

def test_gemini_unconfigured_api_key_fallback():
    # Empty API key should immediately return UNCONFIGURED without making network calls
    svc = GeminiService(api_key="")
    assert svc.is_available() is False

    mock_payload = {
        "domain": "Sales & Retail",
        "file_name": "sales.csv",
        "structured_findings": [],
        "executive_summary_text": "Deterministic fallback summary"
    }

    result = svc.generate_narrative_explanation(mock_payload)
    assert result["status"] == "UNCONFIGURED"
    assert result["fallback_used"] is True
    assert result["ai_summary"] is None

def test_gemini_mocked_narrative_generation():
    svc = GeminiService(api_key="mock_test_key_12345678")
    assert svc.is_available() is True

    mock_response_data = {
        "overall_summary": "Sales in North region increased by 35% with high customer satisfaction.",
        "key_findings": [
            "North region is the highest revenue contributor ($145,000).",
            "UnitsSold and SalesAmount exhibit a strong positive relationship (r = 0.91)."
        ],
        "table_summaries": [
            {"table": "sales.csv", "summary": "Cleaned table with 100 rows and zero remaining defects."}
        ],
        "anomalies": [
            {"finding": "Row 14 Sales Spike", "explanation": "Transaction TX1014 ($120,000) was 4x median."}
        ],
        "data_quality_notes": [
            "One duplicate row removed and missing prices imputed."
        ]
    }

    mock_client = MagicMock()
    mock_model_response = MagicMock()
    mock_model_response.text = json.dumps(mock_response_data)
    mock_client.models.generate_content.return_value = mock_model_response
    svc.client = mock_client

    mock_payload = {
        "domain": "Sales & Retail",
        "file_name": "sales.csv",
        "dataset_overview": {"total_rows": 100},
        "structured_findings": [{"id": "FND_001", "title": "Sales Surge", "evidence": "Math +35%"}],
        "executive_summary_text": "Deterministic summary"
    }

    result = svc.generate_narrative_explanation(mock_payload)
    assert result["status"] == "SUCCESS"
    assert result["fallback_used"] is False
    assert result["ai_summary"] is not None
    assert "North region" in result["ai_summary"]["overall_summary"]
    assert len(result["ai_summary"]["key_findings"]) == 2

def test_gemini_rate_limit_quota_fallback():
    svc = GeminiService(api_key="mock_test_key_12345678")
    
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
    svc.client = mock_client

    mock_payload = {
        "domain": "Finance & Banking",
        "file_name": "finance.xlsx",
        "structured_findings": [],
        "executive_summary_text": "Fallback deterministic summary"
    }

    result = svc.generate_narrative_explanation(mock_payload)
    assert result["status"] == "RATE_LIMIT_QUOTA_EXCEEDED"
    assert result["fallback_used"] is True
    assert result["ai_summary"] is None
