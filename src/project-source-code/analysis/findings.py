from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from models.result_models import Finding, DatasetProfile, AnomalyReport
from config.settings import (
    DOMAIN_KEYWORDS,
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_MODERATE_THRESHOLD,
    SIGNIFICANT_CHANGE_THRESHOLD_PCT,
    GROUP_DIFFERENCE_THRESHOLD_PCT,
    DOMINANT_CATEGORY_THRESHOLD_PCT
)

def detect_structured_findings(
    df: pd.DataFrame,
    profile: DatasetProfile,
    numerical_summary: Dict[str, Dict[str, Any]],
    categorical_summary: Dict[str, Dict[str, Any]],
    group_aggregations: Dict[str, Any],
    correlations: Dict[str, Dict[str, float]],
    trends: Dict[str, Any],
    anomaly_report: AnomalyReport,
    domain: Optional[str] = None
) -> List[Finding]:
    """
    Transforms computed statistics and raw numerical facts into concrete,
    interpretable, machine-readable Finding objects backed by mathematical evidence.
    """
    findings: List[Finding] = []
    domain_hints = DOMAIN_KEYWORDS.get(domain, {}) if domain else {}
    priority_metrics = [k.lower() for k in domain_hints.get("metrics", [])]
    priority_groups = [k.lower() for k in domain_hints.get("groups", [])]

    finding_counter = 1

    def next_id(prefix: str) -> str:
        nonlocal finding_counter
        fid = f"FND_{prefix}_{finding_counter:03d}"
        finding_counter += 1
        return fid

    # -------------------------------------------------------------
    # 1. TIME-SERIES TRENDS & SIGNIFICANT CHRONOLOGICAL CHANGES
    # -------------------------------------------------------------
    if trends and "trend_direction" in trends:
        metric = trends.get("metric_column", "")
        dt_col = trends.get("datetime_column", "")
        pct_chg = trends.get("percentage_change", 0.0)
        direction = trends.get("trend_direction", "Stable")
        first_val = trends.get("first_value", 0.0)
        last_val = trends.get("last_value", 0.0)
        start_d = trends.get("start_date", "")
        end_d = trends.get("end_date", "")

        abs_pct = abs(pct_chg)
        severity = "High" if abs_pct >= 30.0 else "Medium" if abs_pct >= SIGNIFICANT_CHANGE_THRESHOLD_PCT else "Info"
        action_verb = "increased" if pct_chg > 0 else "decreased" if pct_chg < 0 else "remained steady"

        findings.append(Finding(
            id=next_id("TRN"),
            type="TREND" if abs_pct < 25 else "SIGNIFICANT_CHANGE",
            title=f"{metric} {direction} Trend ({pct_chg:+.1f}%)",
            description=f"{metric} {action_verb} by {abs_pct:.1f}% from {first_val:,.2f} to {last_val:,.2f} across the timeline ({start_d} to {end_d}).",
            severity=severity,
            source_columns=[dt_col, metric],
            supporting_values={
                "metric": metric,
                "first_value": first_val,
                "last_value": last_val,
                "percentage_change": pct_chg,
                "start_period": start_d,
                "end_period": end_d,
                "direction": direction
            },
            confidence=0.95,
            category="Temporal",
            evidence=f"Calculated from chronological sequence: ({last_val} - {first_val}) / {first_val} * 100 = {pct_chg:.2f}%."
        ))

        # Check for period-over-period spikes if detailed trend df available
        if "max_positive_step" in trends and "max_negative_step" in trends:
            pos_step = trends["max_positive_step"]
            if pos_step.get("pct_change", 0) >= 20.0:
                findings.append(Finding(
                    id=next_id("SPK"),
                    type="SIGNIFICANT_CHANGE",
                    title=f"Sharp Increase in {metric} ({pos_step['pct_change']:+.1f}%)",
                    description=f"Largest single-period surge occurred between {pos_step['from_date']} and {pos_step['to_date']} (+{pos_step['pct_change']:.1f}%).",
                    severity="Medium",
                    source_columns=[dt_col, metric],
                    supporting_values=pos_step,
                    confidence=0.90,
                    category="Temporal",
                    evidence=f"Value climbed from {pos_step['from_val']} to {pos_step['to_val']} in consecutive periods."
                ))

            neg_step = trends["max_negative_step"]
            if neg_step.get("pct_change", 0) <= -20.0:
                findings.append(Finding(
                    id=next_id("DRP"),
                    type="SIGNIFICANT_CHANGE",
                    title=f"Sharp Drop in {metric} ({neg_step['pct_change']:.1f}%)",
                    description=f"Largest single-period drop occurred between {neg_step['from_date']} and {neg_step['to_date']} ({neg_step['pct_change']:.1f}%).",
                    severity="High",
                    source_columns=[dt_col, metric],
                    supporting_values=neg_step,
                    confidence=0.90,
                    category="Temporal",
                    evidence=f"Value dropped from {neg_step['from_val']} to {neg_step['to_val']} in consecutive periods."
                ))

    # -------------------------------------------------------------
    # 2. GROUP COMPARISONS & PERFORMANCE DISPARITIES
    # -------------------------------------------------------------
    if group_aggregations and "top_group" in group_aggregations:
        grp = group_aggregations
        cat_col = grp.get("grouped_by", "")
        num_col = grp.get("target_metric", "")
        top_grp = grp.get("top_group", {})
        bot_grp = grp.get("bottom_group", {})
        overall_mean = grp.get("overall_mean", 0.0)

        top_cat = top_grp.get("category", "")
        top_mean = top_grp.get("mean", 0.0)
        bot_cat = bot_grp.get("category", "")
        bot_mean = bot_grp.get("mean", 0.0)

        if overall_mean > 0 and top_mean > 0:
            top_diff_pct = round(((top_mean - overall_mean) / overall_mean * 100), 1)
            if top_diff_pct >= GROUP_DIFFERENCE_THRESHOLD_PCT:
                findings.append(Finding(
                    id=next_id("CMP"),
                    type="COMPARISON",
                    title=f"{top_cat} Outperforms Average {num_col} by {top_diff_pct:.1f}%",
                    description=f"In '{cat_col}', group '{top_cat}' averaged {top_mean:,.2f}, which is {top_diff_pct:.1f}% higher than the overall dataset average ({overall_mean:,.2f}).",
                    severity="High" if top_diff_pct >= 50.0 else "Medium",
                    source_columns=[cat_col, num_col],
                    supporting_values={
                        "group_column": cat_col,
                        "metric_column": num_col,
                        "top_group": top_cat,
                        "top_mean": top_mean,
                        "overall_mean": overall_mean,
                        "relative_difference_pct": top_diff_pct
                    },
                    confidence=0.92,
                    category="Performance",
                    evidence=f"Mean difference: ({top_mean} - {overall_mean}) / {overall_mean} * 100 = {top_diff_pct}%."
                ))

        if bot_mean > 0 and top_mean > bot_mean:
            ratio = round(top_mean / bot_mean, 2)
            if ratio >= 1.5:
                findings.append(Finding(
                    id=next_id("DSP"),
                    type="COMPARISON",
                    title=f"Significant Disparity in {num_col} across {cat_col}",
                    description=f"Top group '{top_cat}' ({top_mean:,.2f}) is {ratio}x higher than lowest group '{bot_cat}' ({bot_mean:,.2f}).",
                    severity="High" if ratio >= 2.5 else "Medium",
                    source_columns=[cat_col, num_col],
                    supporting_values={
                        "top_group": top_cat,
                        "bottom_group": bot_cat,
                        "disparity_ratio": ratio,
                        "top_mean": top_mean,
                        "bottom_mean": bot_mean
                    },
                    confidence=0.95,
                    category="Performance",
                    evidence=f"Top-to-bottom ratio: {top_mean} / {bot_mean} = {ratio}x."
                ))

    # -------------------------------------------------------------
    # 3. DOMINANT CATEGORIES & CONCENTRATION
    # -------------------------------------------------------------
    for col, c_info in categorical_summary.items():
        top_pcts = c_info.get("top_percentages", {})
        if top_pcts:
            dominant_name, dominant_pct = next(iter(top_pcts.items()))
            if dominant_pct >= DOMINANT_CATEGORY_THRESHOLD_PCT:
                findings.append(Finding(
                    id=next_id("DOM"),
                    type="DOMINANT_CATEGORY",
                    title=f"High Concentration in '{col}': {dominant_name} ({dominant_pct:.1f}%)",
                    description=f"Category '{dominant_name}' represents {dominant_pct:.1f}% of all records in column '{col}', indicating dominant concentration.",
                    severity="Medium" if dominant_pct >= 60.0 else "Info",
                    source_columns=[col],
                    supporting_values={
                        "column": col,
                        "dominant_category": dominant_name,
                        "percentage": dominant_pct,
                        "unique_count": c_info.get("unique_count", 0)
                    },
                    confidence=0.98,
                    category="Distribution",
                    evidence=f"Value count frequency of '{dominant_name}' is {dominant_pct}% of non-null records."
                ))

        # Rare categories check
        rare_cats = c_info.get("rare_categories", [])
        if rare_cats:
            findings.append(Finding(
                id=next_id("RAR"),
                type="DISTRIBUTION",
                title=f"Rare Categories Detected in '{col}'",
                description=f"Found {len(rare_cats)} low-frequency categories ({', '.join(rare_cats[:3])}) representing <5% of data points.",
                severity="Info",
                source_columns=[col],
                supporting_values={"column": col, "rare_categories": rare_cats},
                confidence=0.90,
                category="Distribution",
                evidence=f"Low sample size per category (<5% of records)."
            ))

    # -------------------------------------------------------------
    # 4. STRONG & MODERATE CORRELATIONS
    # -------------------------------------------------------------
    seen_pairs = set()
    for col1, corr_targets in correlations.items():
        for col2, r_val in corr_targets.items():
            if col1 == col2:
                continue
            pair = tuple(sorted([col1, col2]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            abs_r = abs(r_val)
            if abs_r >= CORRELATION_STRONG_THRESHOLD:
                rel_type = "Strong Positive" if r_val > 0 else "Strong Negative"
                findings.append(Finding(
                    id=next_id("COR"),
                    type="CORRELATION",
                    title=f"{rel_type} Correlation: {col1} & {col2} (r = {r_val:+.2f})",
                    description=f"Columns '{col1}' and '{col2}' exhibit a {rel_type.lower()} linear relationship with Pearson r = {r_val:+.2f}.",
                    severity="High" if abs_r >= 0.85 else "Medium",
                    source_columns=[col1, col2],
                    supporting_values={"column_1": col1, "column_2": col2, "pearson_r": r_val},
                    confidence=0.95,
                    category="Relationship",
                    evidence=f"Pearson correlation coefficient r = {r_val:.4f} exceeds threshold ({CORRELATION_STRONG_THRESHOLD})."
                ))
            elif abs_r >= CORRELATION_MODERATE_THRESHOLD:
                rel_type = "Moderate Positive" if r_val > 0 else "Moderate Negative"
                findings.append(Finding(
                    id=next_id("COR"),
                    type="CORRELATION",
                    title=f"{rel_type} Correlation: {col1} & {col2} (r = {r_val:+.2f})",
                    description=f"Columns '{col1}' and '{col2}' exhibit a {rel_type.lower()} relationship (r = {r_val:+.2f}).",
                    severity="Info",
                    source_columns=[col1, col2],
                    supporting_values={"column_1": col1, "column_2": col2, "pearson_r": r_val},
                    confidence=0.88,
                    category="Relationship",
                    evidence=f"Pearson correlation coefficient r = {r_val:.4f} between {CORRELATION_MODERATE_THRESHOLD} and {CORRELATION_STRONG_THRESHOLD}."
                ))

    # -------------------------------------------------------------
    # 5. STATISTICAL ANOMALIES & EXTREME OBSERVATIONS
    # -------------------------------------------------------------
    if anomaly_report.statistical_anomalies:
        # Group anomalies by column
        col_anom_map: Dict[str, List[Any]] = {}
        for anom in anomaly_report.statistical_anomalies:
            col_anom_map.setdefault(anom.column, []).append(anom)

        for col_name, anom_list in col_anom_map.items():
            top_anom = max(anom_list, key=lambda x: x.score)
            findings.append(Finding(
                id=next_id("ANM"),
                type="ANOMALY",
                title=f"Statistical Anomaly in '{col_name}' (Score {top_anom.score})",
                description=f"Identified {len(anom_list)} statistical outlier(s) in '{col_name}'. Highest deviation observed at row {top_anom.row_index} with value {top_anom.value}.",
                severity="High" if top_anom.score >= 3.0 else "Medium",
                source_columns=[col_name.replace("Multi-variate (", "").replace(")", "").split(",")[0].strip()],
                supporting_values={
                    "column": col_name,
                    "total_outliers": len(anom_list),
                    "max_score": top_anom.score,
                    "row_index": top_anom.row_index,
                    "sample_value": top_anom.value,
                    "method": top_anom.method
                },
                confidence=0.92,
                category="Risk",
                evidence=top_anom.explanation
            ))

    # -------------------------------------------------------------
    # 6. DATA QUALITY FINDINGS
    # -------------------------------------------------------------
    for issue in anomaly_report.data_quality_issues:
        findings.append(Finding(
            id=next_id("DQL"),
            type="DATA_QUALITY",
            title=f"Data Quality: {issue.get('issue_type')} in '{issue.get('column')}'",
            description=issue.get("description", ""),
            severity=issue.get("severity", "Medium"),
            source_columns=[issue.get("column", "")],
            supporting_values=issue,
            confidence=1.0,
            category="Quality",
            evidence=f"Found via deterministic profiling: {issue.get('description', '')}"
        ))

    # -------------------------------------------------------------
    # 7. DOMAIN SPECIFIC PRIORITIZATION & CUSTOM INSIGHTS
    # -------------------------------------------------------------
    # Sort findings by domain relevance, then severity
    def score_finding(f: Finding) -> int:
        score = 0
        if f.severity == "High":
            score += 100
        elif f.severity == "Medium":
            score += 50
        elif f.severity == "Low":
            score += 20
        
        # Boost if touches priority metric or group column
        for c in f.source_columns:
            c_clean = c.lower().replace("_", "").replace(" ", "").replace("-", "")
            if any(pm in c_clean for pm in priority_metrics):
                score += 80
            if any(pg in c_clean for pg in priority_groups):
                score += 40
        return score

    findings.sort(key=score_finding, reverse=True)
    return findings
