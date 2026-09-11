from typing import Dict, Any, List
import pandas as pd
import numpy as np
from models.result_models import AnalysisReport, DatasetProfile

def analyze_statistics(
    df: pd.DataFrame,
    profile: DatasetProfile
) -> AnalysisReport:
    """
    Computes numerical statistics, categorical summaries, group aggregations,
    correlation matrix, and time-series trends.
    """
    numerical_summary: Dict[str, Dict[str, float]] = {}
    categorical_summary: Dict[str, Dict[str, Any]] = {}
    group_aggregations: Dict[str, Any] = {}
    correlations: Dict[str, Dict[str, float]] = {}
    trends: Dict[str, Any] = {}

    # 1. Numerical Statistics
    for col in profile.numerical_columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if not series.empty:
                val_min = float(series.min())
                val_max = float(series.max())
                numerical_summary[col] = {
                    "count": float(len(series)),
                    "sum": float(series.sum()),
                    "mean": round(float(series.mean()), 4),
                    "median": round(float(series.median()), 4),
                    "min": round(val_min, 4),
                    "max": round(val_max, 4),
                    "range": round(val_max - val_min, 4),
                    "std": round(float(series.std()), 4) if len(series) > 1 else 0.0,
                    "q25": round(float(series.quantile(0.25)), 4),
                    "q50": round(float(series.quantile(0.50)), 4),
                    "q75": round(float(series.quantile(0.75)), 4)
                }

    # 2. Categorical Summaries
    for col in profile.categorical_columns:
        if col in df.columns:
            series = df[col].astype(str)
            total_count = len(series)
            val_counts = series.value_counts()
            top_counts = val_counts.head(5).to_dict()
            top_pcts = {k: round((v / total_count * 100), 2) for k, v in top_counts.items()}

            categorical_summary[col] = {
                "unique_count": int(series.nunique()),
                "most_common": str(val_counts.index[0]) if not val_counts.empty else "N/A",
                "top_frequencies": top_counts,
                "top_percentages": top_pcts
            }

    # 3. Group Aggregations (Category x Numeric)
    if profile.categorical_columns and profile.numerical_columns:
        # Select key categorical and numerical columns
        cat_col = profile.categorical_columns[0]
        num_col = profile.numerical_columns[0]
        if cat_col in df.columns and num_col in df.columns:
            grouped = df.groupby(cat_col)[num_col].agg(['mean', 'sum', 'count', 'min', 'max']).reset_index()
            grouped = grouped.sort_values(by='sum', ascending=False)
            
            top_group = grouped.iloc[0] if not grouped.empty else None
            bottom_group = grouped.iloc[-1] if not grouped.empty else None

            group_aggregations = {
                "grouped_by": cat_col,
                "target_metric": num_col,
                "top_group": {
                    "category": str(top_group[cat_col]) if top_group is not None else "N/A",
                    "total_sum": round(float(top_group['sum']), 2) if top_group is not None else 0.0,
                    "mean": round(float(top_group['mean']), 2) if top_group is not None else 0.0
                },
                "bottom_group": {
                    "category": str(bottom_group[cat_col]) if bottom_group is not None else "N/A",
                    "total_sum": round(float(bottom_group['sum']), 2) if bottom_group is not None else 0.0,
                    "mean": round(float(bottom_group['mean']), 2) if bottom_group is not None else 0.0
                },
                "group_table": grouped.head(10).to_dict(orient='records')
            }

    # 4. Correlation Matrix (Numerical x Numerical)
    num_df = df[profile.numerical_columns].select_dtypes(include=[np.number])
    if num_df.shape[1] >= 2:
        corr_matrix = num_df.corr(method='pearson')
        correlations = {
            col: {target: round(float(val), 4) for target, val in row.items()}
            for col, row in corr_matrix.to_dict().items()
        }

    # 5. Trend Analysis (Datetime + Numerical)
    if profile.datetime_columns and profile.numerical_columns:
        dt_col = profile.datetime_columns[0]
        num_col = profile.numerical_columns[0]
        if dt_col in df.columns and num_col in df.columns:
            trend_df = df[[dt_col, num_col]].dropna().copy()
            trend_df[dt_col] = pd.to_datetime(trend_df[dt_col], errors='coerce')
            trend_df = trend_df.dropna().sort_values(by=dt_col)

            if len(trend_df) >= 3:
                first_val = float(trend_df[num_col].iloc[0])
                last_val = float(trend_df[num_col].iloc[-1])
                pct_change = round(((last_val - first_val) / first_val * 100), 2) if first_val != 0 else 0.0

                trend_direction = "Increasing" if pct_change > 2 else "Decreasing" if pct_change < -2 else "Stable"

                trends = {
                    "datetime_column": dt_col,
                    "metric_column": num_col,
                    "start_date": str(trend_df[dt_col].iloc[0]),
                    "end_date": str(trend_df[dt_col].iloc[-1]),
                    "first_value": round(first_val, 2),
                    "last_value": round(last_val, 2),
                    "percentage_change": pct_change,
                    "trend_direction": trend_direction
                }

    return AnalysisReport(
        numerical_summary=numerical_summary,
        categorical_summary=categorical_summary,
        group_aggregations=group_aggregations,
        correlations=correlations,
        trends=trends
    )
