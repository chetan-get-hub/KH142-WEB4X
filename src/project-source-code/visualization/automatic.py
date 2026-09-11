from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from models.result_models import VisualizationResult, DatasetProfile, AnalysisReport
from config.settings import DOMAIN_KEYWORDS

NEON_PALETTE = ['#00E5FF', '#00E676', '#B388FF', '#FFD700', '#FF4081', '#2979FF', '#FF6D00', '#18FFFF']
LIGHT_PALETTE = ['#0284C7', '#059669', '#7C3AED', '#D97706', '#DC2626', '#2563EB', '#EA580C', '#0891B2']

def apply_chart_theme(
    fig: go.Figure,
    title_text: Optional[str] = None,
    theme_mode: str = "dark"
) -> go.Figure:
    """
    Applies responsive visual styling to Plotly charts supporting both Dark Neon and Clean Light themes.
    """
    if theme_mode == "light":
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFC",
            font=dict(family="Inter, -apple-system, sans-serif", color="#0F172A", size=12),
            title=dict(
                text=f"<b>{title_text}</b>" if title_text else None,
                font=dict(color="#0284C7", size=15)
            ) if title_text else None,
            xaxis=dict(
                gridcolor="#E2E8F0",
                linecolor="#CBD5E1",
                zerolinecolor="#CBD5E1",
                tickfont=dict(color="#334155")
            ),
            yaxis=dict(
                gridcolor="#E2E8F0",
                linecolor="#CBD5E1",
                zerolinecolor="#CBD5E1",
                tickfont=dict(color="#334155")
            ),
            legend=dict(
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="#E2E8F0",
                borderwidth=1,
                font=dict(color="#0F172A")
            ),
            margin=dict(l=40, r=30, t=50, b=40)
        )
    else:
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#14141A",
            plot_bgcolor="#181822",
            font=dict(family="Inter, Roboto, sans-serif", color="#F5EEDB", size=12),
            title=dict(
                text=f"<b>{title_text}</b>" if title_text else None,
                font=dict(color="#00E5FF", size=15)
            ) if title_text else None,
            xaxis=dict(
                gridcolor="#282836",
                linecolor="#38384C",
                zerolinecolor="#38384C",
                tickfont=dict(color="#D0C8B8")
            ),
            yaxis=dict(
                gridcolor="#282836",
                linecolor="#38384C",
                zerolinecolor="#38384C",
                tickfont=dict(color="#D0C8B8")
            ),
            legend=dict(
                bgcolor="rgba(20, 20, 26, 0.8)",
                bordercolor="#282836",
                borderwidth=1,
                font=dict(color="#F5EEDB")
            ),
            margin=dict(l=40, r=30, t=50, b=40)
        )
    return fig

apply_neon_theme = apply_chart_theme

def generate_automatic_visualizations(
    df: pd.DataFrame,
    profile: DatasetProfile,
    analysis: AnalysisReport,
    domain: Optional[str] = None,
    theme_mode: str = "dark"
) -> List[VisualizationResult]:
    """
    Intelligently generates purposeful Plotly visualizations answering core analytical questions.
    Supports both Dark Neon and Clean Light modes.
    """
    charts: List[VisualizationResult] = []
    if df.empty:
        return charts

    MAX_VIZ_POINTS = 5000
    plot_df = df.sample(MAX_VIZ_POINTS, random_state=42) if len(df) > MAX_VIZ_POINTS else df.copy()

    domain_target = domain or profile.domain_hint
    domain_hints = DOMAIN_KEYWORDS.get(domain_target, {}) if domain_target else {}
    priority_metrics = [k.lower() for k in domain_hints.get("metrics", [])]
    priority_groups = [k.lower() for k in domain_hints.get("groups", [])]

    palette = NEON_PALETTE if theme_mode == "dark" else LIGHT_PALETTE

    def pick_best_column(candidates: List[str], priority_keywords: List[str]) -> Optional[str]:
        for c in candidates:
            c_clean = c.lower().replace("_", "").replace(" ", "")
            if any(pk in c_clean for pk in priority_keywords):
                return c
        return candidates[0] if candidates else None

    # 1. TIME SERIES LINE CHART
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
                    color_discrete_sequence=[palette[0]]
                )
                apply_chart_theme(fig, f"Chronological Trend: {num_col} over {dt_col}", theme_mode=theme_mode)
                fig.update_traces(line=dict(width=2.5), marker=dict(size=6))
                charts.append(VisualizationResult(
                    chart_id="auto_trend_line",
                    title=f"Trend Analysis: {num_col} vs {dt_col}",
                    chart_type="line",
                    plotly_json=fig.to_json(),
                    description=f"Chronological progression of {num_col} over {dt_col}.",
                    reason=f"Shows chronological movement of key metric {num_col}.",
                    domain_relevance=f"Trend tracking for {domain_target}.",
                    columns_used=[dt_col, num_col],
                    key_takeaway=f"Chronological progression of {num_col} across {len(ts_df)} time points.",
                    analytical_question=f"How does '{num_col}' change chronologically over '{dt_col}'?"
                ))

    # 2. CATEGORICAL BAR CHART
    if profile.categorical_columns and profile.numerical_columns:
        cat_col = pick_best_column(profile.categorical_columns, priority_groups) or profile.categorical_columns[0]
        num_col = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]

        if cat_col in plot_df.columns and num_col in plot_df.columns:
            bar_df = plot_df.groupby(cat_col)[num_col].agg(['mean', 'count']).reset_index()
            bar_df = bar_df.sort_values(by='mean', ascending=False).head(15)

            if len(bar_df) > 1:
                color_scale = [(0, '#101026'), (0.5, '#00E5FF'), (1, '#B388FF')] if theme_mode == "dark" else [(0, '#E0F2FE'), (0.5, '#0284C7'), (1, '#1E40AF')]
                fig = px.bar(
                    bar_df,
                    x=cat_col,
                    y='mean',
                    title=f"Comparative Performance: Average {num_col} by {cat_col}",
                    color='mean',
                    color_continuous_scale=color_scale,
                    text_auto='.2f'
                )
                apply_chart_theme(fig, f"Comparative Performance: Average {num_col} by {cat_col}", theme_mode=theme_mode)
                fig.update_traces(marker_line_width=1.2)
                charts.append(VisualizationResult(
                    chart_id="auto_cat_bar",
                    title=f"Category Breakdown: {num_col} by {cat_col}",
                    chart_type="bar",
                    plotly_json=fig.to_json(),
                    description=f"Comparative performance of {num_col} across {cat_col} categories.",
                    reason=f"Identifies high-performing segments in {cat_col}.",
                    domain_relevance=f"Category benchmarking in {domain_target}.",
                    columns_used=[cat_col, num_col],
                    key_takeaway=f"Top performing group in {cat_col} is '{bar_df.iloc[0][cat_col]}' with mean {bar_df.iloc[0]['mean']:.2f}.",
                    analytical_question=f"Which categories in '{cat_col}' show highest average '{num_col}'?"
                ))

    # 3. NUMERICAL DISTRIBUTION HISTOGRAM
    if profile.numerical_columns:
        target_num = pick_best_column(profile.numerical_columns, priority_metrics) or profile.numerical_columns[0]
        if target_num in plot_df.columns:
            fig = px.histogram(
                plot_df,
                x=target_num,
                nbins=30,
                marginal="box",
                title=f"Distribution Profile: {target_num}",
                color_discrete_sequence=[palette[1] if len(palette) > 1 else palette[0]]
            )
            apply_chart_theme(fig, f"Distribution Profile: {target_num}", theme_mode=theme_mode)
            fig.update_traces(marker_line_width=1)
            charts.append(VisualizationResult(
                chart_id="auto_num_dist",
                title=f"Distribution: {target_num}",
                chart_type="histogram",
                plotly_json=fig.to_json(),
                description=f"Distribution spread and box plot summary of {target_num}.",
                reason=f"Evaluates skewness and dispersion for {target_num}.",
                domain_relevance=f"Statistical range analysis in {domain_target}.",
                columns_used=[target_num],
                key_takeaway=f"Distribution spread of {target_num} across {len(plot_df)} observed points.",
                analytical_question=f"What is the statistical spread and skewness of '{target_num}'?"
            ))

    # 4. MULTIVARIATE SCATTER PLOT
    if len(profile.numerical_columns) >= 2:
        num1 = profile.numerical_columns[0]
        num2 = profile.numerical_columns[1]
        color_col = profile.categorical_columns[0] if profile.categorical_columns else None

        if num1 in plot_df.columns and num2 in plot_df.columns:
            fig = px.scatter(
                plot_df,
                x=num1,
                y=num2,
                color=color_col if color_col and color_col in plot_df.columns else None,
                title=f"Bivariate Correlation: {num1} vs {num2}",
                color_discrete_sequence=palette,
                opacity=0.85
            )
            apply_chart_theme(fig, f"Bivariate Correlation: {num1} vs {num2}", theme_mode=theme_mode)
            fig.update_traces(marker=dict(size=7))
            charts.append(VisualizationResult(
                chart_id="auto_scatter",
                title=f"Correlation Scatter: {num1} vs {num2}",
                chart_type="scatter",
                plotly_json=fig.to_json(),
                description=f"Scatter correlation plot between {num1} and {num2}.",
                reason=f"Examines bivariate relationship between {num1} and {num2}.",
                domain_relevance=f"Correlation study in {domain_target}.",
                columns_used=[num1, num2] + ([color_col] if color_col else []),
                key_takeaway=f"Relationship between {num1} and {num2}.",
                analytical_question=f"How strongly does '{num1}' relate to '{num2}'?"
            ))

    # 5. CORRELATION MATRIX HEATMAP
    if len(profile.numerical_columns) >= 3:
        corr_cols = profile.numerical_columns[:8]
        corr_matrix = plot_df[corr_cols].corr()

        color_scale = [(0, "#00E5FF"), (0.5, "#14141A"), (1, "#FF4081")] if theme_mode == "dark" else [(0, "#0284C7"), (0.5, "#FFFFFF"), (1, "#DC2626")]

        fig = px.imshow(
            corr_matrix,
            text_auto=".2f",
            aspect="auto",
            title="Multivariate Feature Correlation Heatmap",
            color_continuous_scale=color_scale
        )
        apply_chart_theme(fig, "Multivariate Feature Correlation Heatmap", theme_mode=theme_mode)
        charts.append(VisualizationResult(
            chart_id="auto_corr_heatmap",
            title="Correlation Matrix",
            chart_type="heatmap",
            plotly_json=fig.to_json(),
            description="Multivariate correlation heatmap across numerical dimensions.",
            reason="Highlights collinearity and dependencies across features.",
            domain_relevance=f"Inter-variable dependence in {domain_target}.",
            columns_used=corr_cols,
            key_takeaway="Covariance matrix across active numerical dimensions.",
            analytical_question="Which numerical variables exhibit strong positive or negative covariance?"
        ))

    return charts
