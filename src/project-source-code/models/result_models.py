from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

@dataclass
class Finding:
    """
    Structured, machine-readable finding generated from calculated statistical evidence.
    Ready for downstream consumption by LLM or automated reporting.
    """
    id: str
    type: str  # 'TREND', 'COMPARISON', 'CORRELATION', 'DOMINANT_CATEGORY', 'ANOMALY', 'DATA_QUALITY', 'DISTRIBUTION', 'SIGNIFICANT_CHANGE', 'DOMAIN_INSIGHT'
    title: str
    description: str
    severity: str  # 'High', 'Medium', 'Low', 'Info'
    source_columns: List[str]
    supporting_values: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    category: str  # e.g., 'Quality', 'Performance', 'Relationship', 'Temporal', 'Risk'
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "source_columns": self.source_columns,
            "supporting_values": self.supporting_values,
            "confidence": self.confidence,
            "category": self.category,
            "evidence": self.evidence
        }

@dataclass
class ColumnProfile:
    name: str
    inferred_type: str  # 'numerical', 'categorical', 'datetime', 'boolean', 'identifier'
    raw_dtype: str
    missing_count: int
    missing_percentage: float
    unique_count: int
    sample_values: List[Any]
    stats: Dict[str, Any] = field(default_factory=dict)
    role: str = 'general'  # 'measurement', 'grouping', 'temporal', 'identifier', 'general'
    cardinality: str = 'medium'  # 'low', 'medium', 'high'
    suitable_for_grouping: bool = False
    suitable_for_measurement: bool = False
    suitable_for_timeseries: bool = False

@dataclass
class DatasetProfile:
    total_rows: int
    total_columns: int
    file_name: str
    file_type: str
    file_size_bytes: Optional[int]
    columns: Dict[str, ColumnProfile]
    numerical_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]
    boolean_columns: List[str]
    identifier_columns: List[str]
    domain_hint: Optional[str] = None

@dataclass
class CleaningReport:
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    duplicates_found: int
    duplicates_removed: int
    missing_handled_per_column: Dict[str, int]
    total_missing_handled: int
    datatype_conversions: Dict[str, str]
    standardized_columns: List[str]
    outliers_flagged_count: int
    warnings: List[str]
    cleaning_steps: List[Dict[str, Any]]

@dataclass
class AnalysisReport:
    numerical_summary: Dict[str, Dict[str, Any]]
    categorical_summary: Dict[str, Dict[str, Any]]
    group_aggregations: Dict[str, Any]
    correlations: Dict[str, Dict[str, float]]
    trends: Dict[str, Any]
    findings: List[Finding] = field(default_factory=list)
    domain_insights: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AnomalyItem:
    column: str
    row_index: int
    value: Any
    score: float
    method: str  # 'IQR', 'Z-score', 'IsolationForest'
    anomaly_type: str  # 'Statistical Anomaly' vs 'Data Quality Issue' vs 'Unusual Observation'
    explanation: str
    evidence_values: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnomalyReport:
    total_anomalies_found: int
    data_quality_issues: List[Dict[str, Any]]
    statistical_anomalies: List[AnomalyItem]
    method_summaries: Dict[str, int]

@dataclass
class VisualizationResult:
    chart_id: str
    title: str
    chart_type: str
    plotly_json: str
    description: str
    columns_used: List[str] = field(default_factory=list)
    reason: str = ""
    domain_relevance: str = ""

@dataclass
class TableSummary:
    table_name: str
    total_rows: int
    total_columns: int
    data_quality_score: float  # 0 to 100
    key_metrics: Dict[str, Any]
    top_findings: List[Finding]
    anomaly_count: int
    recommended_charts: List[str]

@dataclass
class OverallPipelineResult:
    domain: str
    file_name: str
    sheet_name: Optional[str]
    profile: DatasetProfile
    cleaning_report: CleaningReport
    analysis_report: AnalysisReport
    anomaly_report: AnomalyReport
    automatic_charts: List[VisualizationResult]
    summary_text: str
    table_summaries: List[TableSummary] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)

    def to_serializable_dict(self) -> Dict[str, Any]:
        """
        Export pure structured JSON-ready dictionary (no DataFrames) for future AI/API consumption.
        """
        return {
            "domain": self.domain,
            "file_name": self.file_name,
            "sheet_name": self.sheet_name,
            "dataset_overview": {
                "total_rows": self.profile.total_rows,
                "total_columns": self.profile.total_columns,
                "numerical_columns": self.profile.numerical_columns,
                "categorical_columns": self.profile.categorical_columns,
                "datetime_columns": self.profile.datetime_columns,
                "identifier_columns": self.profile.identifier_columns,
            },
            "cleaning_metrics": {
                "rows_before": self.cleaning_report.rows_before,
                "rows_after": self.cleaning_report.rows_after,
                "duplicates_removed": self.cleaning_report.duplicates_removed,
                "total_missing_handled": self.cleaning_report.total_missing_handled,
                "conversions": self.cleaning_report.datatype_conversions,
                "warnings": self.cleaning_report.warnings
            },
            "statistical_summary": {
                "numerical": self.analysis_report.numerical_summary,
                "categorical": self.analysis_report.categorical_summary,
                "group_aggregations": self.analysis_report.group_aggregations,
                "correlations": self.analysis_report.correlations,
                "trends": self.analysis_report.trends
            },
            "anomaly_summary": {
                "total_anomalies": self.anomaly_report.total_anomalies_found,
                "data_quality_issues": self.anomaly_report.data_quality_issues,
                "method_counts": self.anomaly_report.method_summaries,
                "top_anomalies": [
                    {
                        "column": a.column,
                        "row": a.row_index,
                        "value": a.value,
                        "score": a.score,
                        "method": a.method,
                        "type": a.anomaly_type,
                        "explanation": a.explanation
                    }
                    for a in self.anomaly_report.statistical_anomalies[:10]
                ]
            },
            "structured_findings": [f.to_dict() for f in self.findings],
            "executive_summary_text": self.summary_text
        }
