from typing import Dict, List, Any
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from models.result_models import AnomalyItem, AnomalyReport, DatasetProfile
from config.settings import OUTLIER_IQR_FACTOR, OUTLIER_ZSCORE_THRESHOLD

def detect_anomalies(
    df: pd.DataFrame,
    profile: DatasetProfile
) -> AnomalyReport:
    """
    Detects statistical anomalies and distinguishes them from data quality issues.
    Uses IQR, Z-Score, and Isolation Forest methods.
    """
    data_quality_issues: List[Dict[str, Any]] = []
    statistical_anomalies: List[AnomalyItem] = []
    method_summaries: Dict[str, int] = {"IQR": 0, "Z-score": 0, "IsolationForest": 0}

    # 1. Data Quality Issues (Missing values, high cardinality, zero variance)
    for col, col_prof in profile.columns.items():
        if col_prof.missing_count > 0:
            data_quality_issues.append({
                "column": col,
                "issue_type": "Missing Values",
                "severity": "High" if col_prof.missing_percentage > 20 else "Medium",
                "description": f"Column '{col}' has {col_prof.missing_count} missing value(s) ({col_prof.missing_percentage}%)."
            })
        
        # Zero variance check for numeric columns
        if col_prof.inferred_type == 'numerical' and col in df.columns:
            std_dev = col_prof.stats.get("std", 0.0)
            if std_dev == 0.0 and len(df) > 1:
                data_quality_issues.append({
                    "column": col,
                    "issue_type": "Zero Variance",
                    "severity": "Low",
                    "description": f"Numeric column '{col}' has zero variance (constant value)."
                })

    # 2. Statistical Outliers / Anomalies
    numeric_cols = [c for c in profile.numerical_columns if c in df.columns and c not in profile.identifier_columns]
    
    if numeric_cols and len(df) > 1:
        # A. IQR Method
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue
            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25
            if iqr > 0:
                lower = q25 - (OUTLIER_IQR_FACTOR * iqr)
                upper = q75 + (OUTLIER_IQR_FACTOR * iqr)
                
                iqr_outliers = series[(series < lower) | (series > upper)]
                for idx, val in iqr_outliers.head(10).items():  # Limit top 10 per col
                    method_summaries["IQR"] += 1
                    diff = abs(val - series.median())
                    score = round(diff / iqr, 2) if iqr > 0 else 1.0
                    statistical_anomalies.append(AnomalyItem(
                        column=col,
                        row_index=int(idx),
                        value=float(val) if isinstance(val, (int, float, np.number)) else str(val),
                        score=score,
                        method="IQR",
                        anomaly_type="Statistical Anomaly",
                        explanation=f"Value {val} in '{col}' is outside IQR bounds [{round(lower, 2)}, {round(upper, 2)}]."
                    ))

        # B. Z-Score Method
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue
            mean_val = series.mean()
            std_val = series.std()
            if std_val > 0:
                z_scores = (series - mean_val) / std_val
                z_outliers = series[z_scores.abs() > OUTLIER_ZSCORE_THRESHOLD]
                for idx, val in z_outliers.head(10).items():
                    method_summaries["Z-score"] += 1
                    z_score_val = round(abs((val - mean_val) / std_val), 2)
                    statistical_anomalies.append(AnomalyItem(
                        column=col,
                        row_index=int(idx),
                        value=float(val) if isinstance(val, (int, float, np.number)) else str(val),
                        score=z_score_val,
                        method="Z-score",
                        anomaly_type="Statistical Anomaly",
                        explanation=f"Value {val} in '{col}' has a Z-score of {z_score_val} (> {OUTLIER_ZSCORE_THRESHOLD})."
                    ))

        # C. Isolation Forest for Multi-dimensional Anomaly Detection
        if len(numeric_cols) >= 2 and len(df) >= 5:
            try:
                num_data = df[numeric_cols].fillna(df[numeric_cols].median())
                iso = IsolationForest(contamination=0.05, random_state=42)
                preds = iso.fit_predict(num_data)
                scores = iso.decision_function(num_data)
                
                iso_outlier_indices = np.where(preds == -1)[0]
                for idx in iso_outlier_indices[:5]:  # Top 5 multi-dimensional anomalies
                    method_summaries["IsolationForest"] += 1
                    anom_score = round(float(-scores[idx]), 3)
                    statistical_anomalies.append(AnomalyItem(
                        column="Multi-variate (" + ", ".join(numeric_cols[:3]) + ")",
                        row_index=int(idx),
                        value=str(df.iloc[idx][numeric_cols[:3]].to_dict()),
                        score=anom_score,
                        method="IsolationForest",
                        anomaly_type="Statistical Anomaly",
                        explanation=f"Row {idx} displays a multi-dimensional anomalous pattern across features."
                    ))
            except Exception:
                pass

    total_anomalies = len(statistical_anomalies)

    return AnomalyReport(
        total_anomalies_found=total_anomalies,
        data_quality_issues=data_quality_issues,
        statistical_anomalies=statistical_anomalies,
        method_summaries=method_summaries
    )
