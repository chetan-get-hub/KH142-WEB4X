"""
DC4X: Data Cleaning For You - Pydantic Request & Response Schemas
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DatabaseStatusInfo(BaseModel):
    is_connected: bool
    engine: str
    host: str
    port: int
    database: str
    username: str
    message: str
    connection_locked: bool

class HealthResponse(BaseModel):
    status: str = "ok"
    app_brand: str = "DC4X"
    app_display_name: str = "Data Cleaning For You"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: DatabaseStatusInfo
    gemini_configured: bool
    gemini_connected: bool
    gemini_model: str
    app_env: str

class AnalysisRunCreate(BaseModel):
    domain: str
    file_name: str
    sheet_name: Optional[str] = None
    username: Optional[str] = "analyst@dc4x.io"
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
    category: Optional[str] = "General"
    description: str
    evidence: str
    source_columns: Optional[List[str]] = None

class AnalysisRunResponse(BaseModel):
    run_id: str
    run_code: str
    file_name: str
    domain: str
    sheet_name: Optional[str] = None
    row_count: int
    column_count: int
    data_quality_score: float = 100.0
    status: str
    findings_count: int
    ai_status: str
    ai_summary: Optional[Dict[str, Any]] = None
    deterministic_summary: str
    created_at: Optional[datetime] = None

class DetailedAnalysisRunResponse(AnalysisRunResponse):
    metadata_json: Optional[Dict[str, Any]] = None
    findings: List[FindingItemResponse] = []
