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
    Detects anomalies and strictly classifies them into:
    1. Data Quality Defects (missing values, zero variance, invalid records)
    2. Statistical Outliers (IQR / Z-score / Isolation Forest mathematical deviations)
    3. Potential Important Observations (rare domain-relevant extremes)
    """
    data_quality_issues: List[Dict[str, Any]] = []
    statistical_anomalies: List[AnomalyItem] = []
    method_summaries: Dict[str, int] = {"IQR": 0, "Z-score": 0, "IsolationForest": 0}

    # 1. Data Quality Issues Detection
    for col, col_prof in profile.columns.items():
        if col_prof.missing_count > 0:
            severity = "High" if col_prof.missing_percentage > 20.0 else "Medium"
            data_quality_issues.append({
                "column": col,
                "issue_type": "Missing Values",
                "severity": severity,
                "description": f"Column '{col}' has {col_prof.missing_count} missing value(s) ({col_prof.missing_percentage}% of total rows).",
                "impact": "May bias statistical aggregation and machine learning estimators if unhandled."
            })

        # Zero variance / Constant column check
        if col_prof.inferred_type == 'numerical' and col in df.columns:
            std_dev = col_prof.stats.get("std", 0.0)
            if std_dev == 0.0 and len(df) > 1:
                data_quality_issues.append({
                    "column": col,
                    "issue_type": "Zero Variance / Constant",
                    "severity": "Low",
                    "description": f"Numeric column '{col}' has zero variance (constant value throughout all rows).",
                    "impact": "Provides no analytical variance or predictive signal."
                })

        # High cardinality in categorical column
        if col_prof.inferred_type == 'categorical' and col_prof.unique_count == len(df) and len(df) > 10:
            if col not in profile.identifier_columns:
                data_quality_issues.append({
                    "column": col,
                    "issue_type": "High Cardinality Text",
                    "severity": "Low",
                    "description": f"Text column '{col}' has 100% unique values ({col_prof.unique_count} unique values).",
                    "impact": "Likely represents an unindexed key/identifier rather than an analytical grouping dimension."
                })

    # 2. Statistical Outliers & Observations Detection
    numeric_cols = [
        c for c in profile.numerical_columns
        if c in df.columns and c not in profile.identifier_columns
    ]

    if numeric_cols and len(df) > 1:
        # A. Interquartile Range (IQR) Method
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue
            q25 = float(series.quantile(0.25))
            q75 = float(series.quantile(0.75))
            iqr = q75 - q25
            median_val = float(series.median())

            if iqr > 0:
                lower = q25 - (OUTLIER_IQR_FACTOR * iqr)
                upper = q75 + (OUTLIER_IQR_FACTOR * iqr)

                iqr_outliers = series[(series < lower) | (series > upper)]
                for idx, val in iqr_outliers.head(10).items():
                    method_summaries["IQR"] += 1
                    diff = abs(val - median_val)
                    score = round(diff / iqr, 2)
                    pct_from_med = round((diff / median_val * 100), 1) if median_val != 0 else 0.0

                    # Classify between statistical anomaly vs domain observation
                    anomaly_class = "Statistical Anomaly" if score >= 2.0 else "Unusual Observation"

                    statistical_anomalies.append(AnomalyItem(
                        column=col,
                        row_index=int(idx),
                        value=float(val) if isinstance(val, (int, float, np.number)) else str(val),
                        score=score,
                        method="IQR",
                        anomaly_type=anomaly_class,
                        explanation=f"Value {val:,.2f} in '{col}' falls outside IQR fence [{lower:,.2f}, {upper:,.2f}] ({pct_from_med:+.1f}% vs median {median_val:,.2f}).",
                        evidence_values={
                            "q25": q25,
                            "q75": q75,
                            "iqr": iqr,
                            "lower_fence": lower,
                            "upper_fence": upper,
                            "median": median_val,
                            "deviation_pct": pct_from_med
                        }
                    ))

        # B. Standardized Z-Score Method
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue
            mean_val = float(series.mean())
            std_val = float(series.std())

            if std_val > 0:
                z_scores = (series - mean_val) / std_val
                z_outliers = series[z_scores.abs() > OUTLIER_ZSCORE_THRESHOLD]

                for idx, val in z_outliers.head(10).items():
                    method_summaries["Z-score"] += 1
                    z_score_val = round(abs(float((val - mean_val) / std_val)), 2)

                    statistical_anomalies.append(AnomalyItem(
                        column=col,
                        row_index=int(idx),
                        value=float(val) if isinstance(val, (int, float, np.number)) else str(val),
                        score=z_score_val,
                        method="Z-score",
                        anomaly_type="Statistical Anomaly",
                        explanation=f"Observed value {val:,.2f} is {z_score_val} standard deviations from mean ({mean_val:,.2f} ± {std_val:,.2f}).",
                        evidence_values={
                            "mean": mean_val,
                            "std": std_val,
                            "z_score": z_score_val
                        }
                    ))

        # C. Multi-Dimensional Isolation Forest
        if len(numeric_cols) >= 2 and len(df) >= 5:
            try:
                num_data = df[numeric_cols].fillna(df[numeric_cols].median())
                iso = IsolationForest(contamination=min(0.1, max(0.01, 2 / len(df))), random_state=42)
                preds = iso.fit_predict(num_data)
                scores = iso.decision_function(num_data)

                iso_outlier_indices = np.where(preds == -1)[0]
                for idx in iso_outlier_indices[:5]:
                    method_summaries["IsolationForest"] += 1
                    anom_score = round(float(-scores[idx]), 3)
                    row_dict = {k: round(float(v), 2) if isinstance(v, (int, float, np.number)) else str(v) for k, v in df.iloc[idx][numeric_cols[:4]].to_dict().items()}

                    statistical_anomalies.append(AnomalyItem(
                        column=f"Multi-variate ({', '.join(numeric_cols[:3])})",
                        row_index=int(idx),
                        value=str(row_dict),
                        score=anom_score,
                        method="IsolationForest",
                        anomaly_type="Statistical Anomaly",
                        explanation=f"Row {idx} exhibits an anomalous multi-dimensional profile across numerical metrics.",
                        evidence_values={
                            "isolation_score": anom_score,
                            "features_evaluated": numeric_cols[:4]
                        }
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
