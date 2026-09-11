from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database_connected: bool
    database_message: str
    gemini_configured: bool
    gemini_model: str
    app_env: str

class AnalysisRunCreate(BaseModel):
    domain: str
    file_name: str
    sheet_name: Optional[str] = None
    username: Optional[str] = "analyst@datacleaning4u.io"
    trigger_ai_summary: bool = True
    dataset_overview: Dict[str, Any]
    cleaning_metrics: Dict[str, Any]
    statistical_summary: Dict[str, Any]
    anomaly_summary: Dict[str, Any]
    structured_findings: List[Dict[str, Any]]
    executive_summary_text: str

class FindingItemResponse(BaseModel):
    finding_id: str
    finding_type: str
    title: str
    severity: str
    confidence: float
    description: str
    evidence: str

class AnalysisRunResponse(BaseModel):
    run_id: str
    file_name: str
    domain: str
    sheet_name: Optional[str] = None
    row_count: int
    column_count: int
    status: str
    findings_count: int
    ai_status: str
    ai_summary: Optional[Dict[str, Any]] = None
    deterministic_summary: str
    created_at: datetime
