from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from models.result_models import VisualizationResult, DatasetProfile, AnalysisReport

def generate_automatic_visualizations(
    df: pd.DataFrame,
    profile: DatasetProfile,
    analysis: AnalysisReport
) -> List[VisualizationResult]:
    """
    Automatically selects and constructs meaningful Plotly charts based on column types.
    """
    charts: List[VisualizationResult] = []

    # Modern color palette
    color_sequence = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4']

    # 1. DATETIME + NUMERIC -> Line Chart (Time Series)
    if profile.datetime_columns and profile.numerical_columns:
        dt_col = profile.datetime_columns[0]
        num_col = profile.numerical_columns[0]
        if dt_col in df.columns and num_col in df.columns:
            plot_df = df[[dt_col, num_col]].dropna().copy()
            plot_df[dt_col] = pd.to_datetime(plot_df[dt_col], errors='coerce')
            plot_df = plot_df.dropna().sort_values(by=dt_col)

            fig = px.line(
                plot_df,
                x=dt_col,
                y=num_col,
                title=f"Trend Over Time: {num_col} vs {dt_col}",
                markers=True,
                color_discrete_sequence=['#6366F1']
            )
            fig.update_layout(
                template="plotly_white",
                xaxis_title=dt_col,
                yaxis_title=num_col,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_line_trend",
                title=f"Trend Over Time ({num_col})",
                chart_type="Line Chart",
                plotly_json=fig.to_json(),
                description=f"Chronological line chart showing movement in {num_col} across {dt_col}."
            ))

    # 2. CATEGORY + NUMERIC -> Bar Chart
    if profile.categorical_columns and profile.numerical_columns:
        cat_col = profile.categorical_columns[0]
        num_col = profile.numerical_columns[0]
        if cat_col in df.columns and num_col in df.columns:
            grouped = df.groupby(cat_col, as_index=False)[num_col].agg('sum')
            grouped = grouped.sort_values(by=num_col, ascending=False).head(10)

            fig = px.bar(
                grouped,
                x=cat_col,
                y=num_col,
                title=f"Total {num_col} by Category ({cat_col})",
                color=cat_col,
                color_discrete_sequence=color_sequence
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
                title=f"{num_col} Breakdown by {cat_col}",
                chart_type="Bar Chart",
                plotly_json=fig.to_json(),
                description=f"Bar chart highlighting total {num_col} per category in {cat_col}."
            ))

    # 3. NUMERIC + NUMERIC -> Scatter Plot
    if len(profile.numerical_columns) >= 2:
        num_col1 = profile.numerical_columns[0]
        num_col2 = profile.numerical_columns[1]
        if num_col1 in df.columns and num_col2 in df.columns:
            hover_cat = profile.categorical_columns[0] if profile.categorical_columns and profile.categorical_columns[0] in df.columns else None

            fig = px.scatter(
                df,
                x=num_col1,
                y=num_col2,
                color=hover_cat,
                title=f"Relationship: {num_col1} vs {num_col2}",
                color_discrete_sequence=color_sequence
            )
            fig.update_layout(
                template="plotly_white",
                xaxis_title=num_col1,
                yaxis_title=num_col2,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_scatter_rel",
                title=f"{num_col1} vs {num_col2} Relationship",
                chart_type="Scatter Plot",
                plotly_json=fig.to_json(),
                description=f"Scatter plot demonstrating correlation and clustering between {num_col1} and {num_col2}."
            ))

    # 4. NUMERIC DISTRIBUTION -> Histogram & Box Plot
    if profile.numerical_columns:
        num_col = profile.numerical_columns[0]
        if num_col in df.columns:
            # Histogram
            fig_hist = px.histogram(
                df,
                x=num_col,
                nbins=20,
                title=f"Distribution Frequency: {num_col}",
                color_discrete_sequence=['#10B981']
            )
            fig_hist.update_layout(
                template="plotly_white",
                xaxis_title=num_col,
                yaxis_title="Count",
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_hist_dist",
                title=f"Frequency Distribution ({num_col})",
                chart_type="Histogram",
                plotly_json=fig_hist.to_json(),
                description=f"Histogram showcasing spread, skewness, and frequency of {num_col}."
            ))

            # Box Plot
            cat_col = profile.categorical_columns[0] if profile.categorical_columns and profile.categorical_columns[0] in df.columns else None
            fig_box = px.box(
                df,
                y=num_col,
                x=cat_col,
                title=f"Box Plot & Outliers: {num_col}",
                color=cat_col,
                color_discrete_sequence=color_sequence
            )
            fig_box.update_layout(
                template="plotly_white",
                yaxis_title=num_col,
                margin=dict(l=40, r=40, t=60, b=40)
            )

            charts.append(VisualizationResult(
                chart_id="auto_box_dist",
                title=f"Box Plot & Outlier Spread ({num_col})",
                chart_type="Box Plot",
                plotly_json=fig_box.to_json(),
                description=f"Box plot representing quartiles, median, and extreme values for {num_col}."
            ))

    # 5. MULTIPLE NUMERIC COLUMNS -> Correlation Heatmap
    num_df = df[profile.numerical_columns].select_dtypes(include=[np.number])
    if num_df.shape[1] >= 2:
        corr_matrix = num_df.corr().round(2)
        fig_heat = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Viridis",
            title="Numerical Correlation Heatmap"
        )
        fig_heat.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=40, t=60, b=40)
        )

        charts.append(VisualizationResult(
            chart_id="auto_heatmap_corr",
            title="Feature Correlation Heatmap",
            chart_type="Heatmap",
            plotly_json=fig_heat.to_json(),
            description="Matrix illustrating pairwise linear relationships across numerical columns."
        ))

    return charts
