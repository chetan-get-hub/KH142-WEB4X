from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from models.result_models import VisualizationResult, DatasetProfile, AnalysisReport
from config.settings import DOMAIN_KEYWORDS

def generate_automatic_visualizations(
    df: pd.DataFrame,
    profile: DatasetProfile,
    analysis: AnalysisReport,
    domain: Optional[str] = None
) -> List[VisualizationResult]:
    """
    Intelligently generates purposeful Plotly visualizations answering core analytical questions.
    Uses datatype classification, cardinality, and domain priorities.
    """
    charts: List[VisualizationResult] = []
    if df.empty:
        return charts

    # Safety: sample for visualization rendering if dataset is large
    MAX_VIZ_POINTS = 5000
    plot_df = df.sample(MAX_VIZ_POINTS, random_state=42) if len(df) > MAX_VIZ_POINTS else df.copy()

    # Modern color palette
    color_palette = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#3B82F6']

    domain_target = domain or profile.domain_hint
    domain_hints = DOMAIN_KEYWORDS.get(domain_target, {}) if domain_target else {}
    priority_metrics = [k.lower() for k in domain_hints.get("metrics", [])]
    priority_groups = [k.lower() for k in domain_hints.get("groups", [])]

    # Prioritize columns
    def pick_best_column(candidates: List[str], priority_keywords: List[str]) -> Optional[str]:
        for c in candidates:
            c_clean = c.lower().replace("_", "").replace(" ", "")
            if any(pk in c_clean for pk in priority_keywords):
                return c
        return candidates[0] if candidates else None

    # 1. TIME SERIES LINE CHART: How does the primary metric evolve over time?
    if profile.datetime_columns and profile.numerical_columns:
        dt_col = profile.datetime_columns[0]
        num_col = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]

        if dt_col in plot_df.columns and num_col in plot_df.columns:
            ts_df = plot_df[[dt_col, num_col]].dropna().copy()
            ts_df[dt_col] = pd.to_datetime(ts_df[dt_col], errors='coerce')
            ts_df = ts_df.dropna().sort_values(by=dt_col)

            if len(ts_df) >= 2:
                fig = px.line(
                    ts_df,
                    x=dt_col,
                    y=num_col,
                    title=f"Chronological Trend: {num_col} over {dt_col}",
                    markers=True,
                    color_discrete_sequence=['#4F46E5']
                )
                fig.update_layout(
                    template="plotly_white",
                    xaxis_title=dt_col,
                    yaxis_title=num_col,
                    margin=dict(l=40, r=40, t=60, b=40)
                )

                charts.append(VisualizationResult(
                    chart_id="auto_line_trend",
                    title=f"Chronological Movement of {num_col}",
                    chart_type="Line Chart",
                    plotly_json=fig.to_json(),
                    description=f"Tracks historical change, peaks, and dips in {num_col} across the {dt_col} timeline.",
                    columns_used=[dt_col, num_col],
                    reason="Answers: How is the primary metric trending over time?",
                    domain_relevance=f"Highlights longitudinal performance for {domain_target or 'the business'}."
                ))

    # 2. CATEGORICAL BAR CHART: Which categories generate the highest metric volume?
    if profile.categorical_columns and profile.numerical_columns:
        cat_candidates = [c for c in profile.categorical_columns if profile.columns[c].suitable_for_grouping] or profile.categorical_columns
        cat_col = pick_best_column(cat_candidates, priority_groups) or cat_candidates[0]
        num_col = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]

        if cat_col in plot_df.columns and num_col in plot_df.columns:
            grouped = plot_df.groupby(cat_col, as_index=False)[num_col].agg(['sum', 'mean']).reset_index()
            grouped = grouped.sort_values(by='sum', ascending=False).head(12)

            fig = px.bar(
                grouped,
                x=cat_col,
                y='sum',
                title=f"Total {num_col} by {cat_col}",
                color=cat_col,
                color_discrete_sequence=color_palette,
                text_auto='.2s'
            )
            fig.update_layout(
                template="plotly_white",
                xaxis_title=cat_col,
                yaxis_title=f"Total {num_col}",
                showlegend=False,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_bar_category",
                title=f"{num_col} Volume by {cat_col}",
                chart_type="Bar Chart",
                plotly_json=fig.to_json(),
                description=f"Identifies high-volume and lagging segments in {cat_col} ranked by cumulative {num_col}.",
                columns_used=[cat_col, num_col],
                reason=f"Answers: Which {cat_col} categories contribute most to {num_col}?",
                domain_relevance=f"Enables categorical benchmarking for {domain_target or 'the organization'}."
            ))

    # 3. SCATTER PLOT: What is the relationship between two numerical drivers?
    if len(profile.numerical_columns) >= 2:
        num1 = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]
        rem_nums = [c for c in profile.numerical_columns if c != num1]
        num2 = pick_best_column(rem_nums, priority_metrics) or rem_nums[0]

        if num1 in plot_df.columns and num2 in plot_df.columns:
            hover_cat = profile.categorical_columns[0] if profile.categorical_columns and profile.categorical_columns[0] in plot_df.columns else None

            fig = px.scatter(
                plot_df,
                x=num1,
                y=num2,
                color=hover_cat,
                title=f"Driver Relationship: {num1} vs {num2}",
                color_discrete_sequence=color_palette
            )
            fig.update_layout(
                template="plotly_white",
                xaxis_title=num1,
                yaxis_title=num2,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_scatter_rel",
                title=f"Relationship: {num1} vs {num2}",
                chart_type="Scatter Plot",
                plotly_json=fig.to_json(),
                description=f"Demonstrates correlation, clustering patterns, and linearity between {num1} and {num2}.",
                columns_used=[num1, num2] + ([hover_cat] if hover_cat else []),
                reason=f"Answers: Does a change in {num1} correspond to a change in {num2}?",
                domain_relevance="Assesses inter-variable dependencies."
            ))

    # 4. DISTRIBUTION HISTOGRAM & BOX PLOT: How is the primary metric spread?
    if profile.numerical_columns:
        num_col = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]
        if num_col in plot_df.columns:
            cat_group = pick_best_column(profile.categorical_columns, priority_groups) if profile.categorical_columns else None

            # Box Plot with Outlier Overlay
            fig_box = px.box(
                plot_df,
                y=num_col,
                x=cat_group,
                color=cat_group,
                title=f"Distribution Spread & Outliers: {num_col}",
                color_discrete_sequence=color_palette,
                points="all"
            )
            fig_box.update_layout(
                template="plotly_white",
                yaxis_title=num_col,
                showlegend=False,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_box_spread",
                title=f"Spread & Outlier Analysis ({num_col})",
                chart_type="Box Plot",
                plotly_json=fig_box.to_json(),
                description=f"Highlights median, interquartile range (IQR), and individual anomalous data points for {num_col}.",
                columns_used=[num_col] + ([cat_group] if cat_group else []),
                reason=f"Answers: What is the distribution shape and variance of {num_col}?",
                domain_relevance="Pinpoints outlier variance and operational dispersion."
            ))

    # 5. CORRELATION HEATMAP: Multi-variable correlation overview
    num_df = plot_df[profile.numerical_columns].select_dtypes(include=[np.number])
    if num_df.shape[1] >= 2:
        corr_matrix = num_df.corr().round(2)
        fig_heat = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1.0,
            zmax=1.0,
            title="Numerical Feature Correlation Matrix"
        )
        fig_heat.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=60, b=40)
        )

        charts.append(VisualizationResult(
            chart_id="auto_heatmap_corr",
            title="Multi-Feature Correlation Heatmap",
            chart_type="Heatmap",
            plotly_json=fig_heat.to_json(),
            description="Comprehensive matrix illustrating pairwise linear correlations across all numerical attributes.",
            columns_used=list(corr_matrix.columns),
            reason="Answers: Which numerical attributes move together across the entire dataset?",
            domain_relevance="Identifies co-linear factors."
        ))

    return charts
