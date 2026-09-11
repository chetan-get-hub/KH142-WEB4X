from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

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
    numerical_summary: Dict[str, Dict[str, float]]
    categorical_summary: Dict[str, Dict[str, Any]]
    group_aggregations: Dict[str, Any]
    correlations: Dict[str, Dict[str, float]]
    trends: Dict[str, Any]

@dataclass
class AnomalyItem:
    column: str
    row_index: int
    value: Any
    score: float
    method: str  # 'IQR', 'Z-score', 'IsolationForest'
    anomaly_type: str  # 'Statistical Anomaly' vs 'Data Quality Issue'
    explanation: str

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
