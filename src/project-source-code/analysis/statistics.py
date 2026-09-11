from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.result_models import AnalysisReport, DatasetProfile, Finding
from analysis.findings import detect_structured_findings
from config.settings import DOMAIN_KEYWORDS

def analyze_statistics(
    df: pd.DataFrame,
    profile: DatasetProfile,
    anomaly_report: Optional[Any] = None,
    domain: Optional[str] = None
) -> AnalysisReport:
    """
    Advanced Statistical Engine.
    Computes numerical statistics, categorical summaries, group aggregations,
    correlation matrix, chronological time-series trends, and structured findings.
    """
    numerical_summary: Dict[str, Dict[str, Any]] = {}
    categorical_summary: Dict[str, Dict[str, Any]] = {}
    group_aggregations: Dict[str, Any] = {}
    correlations: Dict[str, Dict[str, float]] = {}
    trends: Dict[str, Any] = {}
    domain_insights: List[Dict[str, Any]] = []

    domain_target = domain or profile.domain_hint
    domain_hints = DOMAIN_KEYWORDS.get(domain_target, {}) if domain_target else {}
    priority_metrics = [k.lower() for k in domain_hints.get("metrics", [])]
    priority_groups = [k.lower() for k in domain_hints.get("groups", [])]

    # 1. Numerical Statistics Engine
    for col in profile.numerical_columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            series = df[col].dropna()
            if not series.empty:
                val_min = float(series.min())
                val_max = float(series.max())
                val_mean = float(series.mean())
                val_median = float(series.median())
                val_std = float(series.std()) if len(series) > 1 else 0.0
                val_var = float(series.var()) if len(series) > 1 else 0.0
                q25 = float(series.quantile(0.25))
                q50 = float(series.quantile(0.50))
                q75 = float(series.quantile(0.75))
                iqr = q75 - q25
                cv = (val_std / val_mean * 100) if val_mean != 0 else 0.0

                numerical_summary[col] = {
                    "count": float(len(series)),
                    "sum": round(float(series.sum()), 4),
                    "mean": round(val_mean, 4),
                    "median": round(val_median, 4),
                    "min": round(val_min, 4),
                    "max": round(val_max, 4),
                    "range": round(val_max - val_min, 4),
                    "std": round(val_std, 4),
                    "variance": round(val_var, 4),
                    "q25": round(q25, 4),
                    "q50": round(q50, 4),
                    "q75": round(q75, 4),
                    "iqr": round(iqr, 4),
                    "cv_percent": round(cv, 2)
                }

    # 2. Categorical Summaries Engine
    for col in profile.categorical_columns + profile.boolean_columns:
        if col in df.columns:
            series = df[col].astype(str)
            total_count = len(series)
            val_counts = series.value_counts()
            top_counts = val_counts.head(5).to_dict()
            top_pcts = {k: round((v / total_count * 100), 2) for k, v in top_counts.items()} if total_count > 0 else {}

            # Identify rare categories (< 5% frequency)
            rare_cats = [str(k) for k, v in val_counts.items() if (v / total_count < 0.05) and len(val_counts) > 2]

            categorical_summary[col] = {
                "unique_count": int(series.nunique()),
                "most_common": str(val_counts.index[0]) if not val_counts.empty else "N/A",
                "top_frequencies": top_counts,
                "top_percentages": top_pcts,
                "rare_categories": rare_cats[:5]
            }

    # 3. Group Aggregations Engine (Prioritized by domain hints)
    cat_candidates = [c for c in profile.categorical_columns if profile.columns[c].suitable_for_grouping] or profile.categorical_columns
    num_candidates = [c for c in profile.numerical_columns if profile.columns[c].suitable_for_measurement] or profile.numerical_columns

    if cat_candidates and num_candidates:
        # Domain-aware prioritization of grouping column & metric column
        best_cat = None
        for cand in cat_candidates:
            cand_clean = cand.lower().replace("_", "").replace(" ", "")
            if any(pg in cand_clean for pg in priority_groups):
                best_cat = cand
                break
        cat_col = best_cat or cat_candidates[0]

        best_num = None
        for cand in num_candidates:
            cand_clean = cand.lower().replace("_", "").replace(" ", "")
            if any(pm in cand_clean for pm in priority_metrics):
                best_num = cand
                break
        num_col = best_num or num_candidates[0]

        if cat_col in df.columns and num_col in df.columns:
            grouped = df.groupby(cat_col)[num_col].agg(['mean', 'sum', 'count', 'min', 'max']).reset_index()
            grouped = grouped.sort_values(by='mean', ascending=False)
            overall_mean = float(df[num_col].mean()) if not df[num_col].dropna().empty else 0.0

            top_group = grouped.iloc[0] if not grouped.empty else None
            bottom_group = grouped.iloc[-1] if not grouped.empty else None

            group_aggregations = {
                "grouped_by": cat_col,
                "target_metric": num_col,
                "overall_mean": round(overall_mean, 2),
                "top_group": {
                    "category": str(top_group[cat_col]) if top_group is not None else "N/A",
                    "total_sum": round(float(top_group['sum']), 2) if top_group is not None else 0.0,
                    "mean": round(float(top_group['mean']), 2) if top_group is not None else 0.0,
                    "count": int(top_group['count']) if top_group is not None else 0
                },
                "bottom_group": {
                    "category": str(bottom_group[cat_col]) if bottom_group is not None else "N/A",
                    "total_sum": round(float(bottom_group['sum']), 2) if bottom_group is not None else 0.0,
                    "mean": round(float(bottom_group['mean']), 2) if bottom_group is not None else 0.0,
                    "count": int(bottom_group['count']) if bottom_group is not None else 0
                },
                "group_table": grouped.head(10).to_dict(orient='records')
            }

    # 4. Correlation Matrix Engine
    num_df = df[profile.numerical_columns].select_dtypes(include=[np.number])
    if num_df.shape[1] >= 2:
        corr_matrix = num_df.corr(method='pearson')
        correlations = {
            col: {target: round(float(val), 4) for target, val in row.items()}
            for col, row in corr_matrix.to_dict().items()
        }

    # 5. Chronological Trend Analysis Engine
    if profile.datetime_columns and profile.numerical_columns:
        # Choose best temporal and measure column
        dt_col = profile.datetime_columns[0]
        num_col = group_aggregations.get("target_metric", profile.numerical_columns[0]) if group_aggregations else profile.numerical_columns[0]

        if dt_col in df.columns and num_col in df.columns:
            trend_df = df[[dt_col, num_col]].dropna().copy()
            trend_df[dt_col] = pd.to_datetime(trend_df[dt_col], errors='coerce')
            trend_df = trend_df.dropna().sort_values(by=dt_col).reset_index(drop=True)

            if len(trend_df) >= 2:
                first_val = float(trend_df[num_col].iloc[0])
                last_val = float(trend_df[num_col].iloc[-1])
                pct_change = round(((last_val - first_val) / first_val * 100), 2) if first_val != 0 else 0.0
                trend_direction = "Increasing" if pct_change > 2 else "Decreasing" if pct_change < -2 else "Stable"

                # Period-over-period steps
                max_pos_step = {"pct_change": 0.0, "from_date": "", "to_date": "", "from_val": 0, "to_val": 0}
                max_neg_step = {"pct_change": 0.0, "from_date": "", "to_date": "", "from_val": 0, "to_val": 0}

                if len(trend_df) >= 3:
                    for i in range(len(trend_df) - 1):
                        v_prev = float(trend_df[num_col].iloc[i])
                        v_curr = float(trend_df[num_col].iloc[i+1])
                        d_prev = str(trend_df[dt_col].iloc[i])
                        d_curr = str(trend_df[dt_col].iloc[i+1])
                        if v_prev != 0:
                            step_pct = round(((v_curr - v_prev) / v_prev * 100), 2)
                            if step_pct > max_pos_step["pct_change"]:
                                max_pos_step = {
                                    "pct_change": step_pct,
                                    "from_date": d_prev,
                                    "to_date": d_curr,
                                    "from_val": round(v_prev, 2),
                                    "to_val": round(v_curr, 2)
                                }
                            if step_pct < max_neg_step["pct_change"]:
                                max_neg_step = {
                                    "pct_change": step_pct,
                                    "from_date": d_prev,
                                    "to_date": d_curr,
                                    "from_val": round(v_prev, 2),
                                    "to_val": round(v_curr, 2)
                                }

                trends = {
                    "datetime_column": dt_col,
                    "metric_column": num_col,
                    "start_date": str(trend_df[dt_col].iloc[0]),
                    "end_date": str(trend_df[dt_col].iloc[-1]),
                    "first_value": round(first_val, 2),
                    "last_value": round(last_val, 2),
                    "percentage_change": pct_change,
                    "trend_direction": trend_direction,
                    "max_positive_step": max_pos_step,
                    "max_negative_step": max_neg_step
                }

    # 6. Generate Machine-Readable Findings if anomaly report available
    findings: List[Finding] = []
    if anomaly_report is not None:
        findings = detect_structured_findings(
            df=df,
            profile=profile,
            numerical_summary=numerical_summary,
            categorical_summary=categorical_summary,
            group_aggregations=group_aggregations,
            correlations=correlations,
            trends=trends,
            anomaly_report=anomaly_report,
            domain=domain_target
        )

    return AnalysisReport(
        numerical_summary=numerical_summary,
        categorical_summary=categorical_summary,
        group_aggregations=group_aggregations,
        correlations=correlations,
        trends=trends,
        findings=findings,
        domain_insights=domain_insights
    )
