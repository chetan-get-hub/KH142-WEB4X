from typing import Optional, List
import pandas as pd
import numpy as np
import plotly.express as px
from models.result_models import VisualizationResult, DatasetProfile
from visualization.automatic import apply_chart_theme, NEON_PALETTE, LIGHT_PALETTE

class ChartValidationError(Exception):
    """Exception raised when user selected chart parameters are invalid or incompatible."""
    pass

def build_custom_visualization(
    df: pd.DataFrame,
    profile: DatasetProfile,
    chart_type: str,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    group_col: Optional[str] = None,
    theme_mode: str = "dark"
) -> VisualizationResult:
    """
    Builds a custom user-requested chart with strict parameter validation,
    meaningful error messages, and responsive dark/light theme support.
    """
    if df.empty:
        raise ChartValidationError("Cannot generate chart from an empty dataset.")

    MAX_POINTS = 5000
    plot_df = df.sample(MAX_POINTS, random_state=42) if len(df) > MAX_POINTS else df.copy()

    palette = NEON_PALETTE if theme_mode == "dark" else LIGHT_PALETTE
    chart_type_clean = chart_type.strip().title()

    # 1. Bar Chart
    if chart_type_clean in ["Bar Chart", "Bar"]:
        if not x_col or not y_col:
            raise ChartValidationError("Bar charts require selecting both an X Axis category and a Y Axis numerical metric.")
        if y_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[y_col]):
            raise ChartValidationError(f"Y Axis for Bar Chart must be numerical. Column '{y_col}' is not numeric.")

        grp_cols = [x_col]
        if group_col and group_col != "None" and group_col in df.columns and group_col != x_col:
            grp_cols.append(group_col)

        grouped = plot_df.groupby(grp_cols, as_index=False)[y_col].agg('sum').head(35)

        fig = px.bar(
            grouped,
            x=x_col,
            y=y_col,
            color=group_col if group_col and group_col != "None" and group_col in df.columns else x_col,
            barmode="group" if group_col and group_col != "None" else "relative",
            title=f"Custom Bar Chart: {y_col} by {x_col}",
            color_discrete_sequence=palette,
            text_auto='.2s'
        )
        apply_chart_theme(fig, f"Custom Bar Chart: {y_col} by {x_col}", theme_mode=theme_mode)
        fig.update_traces(marker_line_width=1.2)

    # 2. Line Chart
    elif chart_type_clean in ["Line Chart", "Line"]:
        if not x_col or not y_col:
            raise ChartValidationError("Line charts require selecting both X Axis and Y Axis columns.")
        if y_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[y_col]):
            raise ChartValidationError(f"Y Axis for Line Chart must be numerical. Column '{y_col}' is not numeric.")

        cols_to_keep = [x_col, y_col]
        has_grp = group_col and group_col != "None" and group_col in df.columns
        if has_grp:
            cols_to_keep.append(group_col)

        line_df = plot_df[cols_to_keep].dropna().copy()
        if x_col in profile.datetime_columns or pd.api.types.is_datetime64_any_dtype(line_df[x_col]):
            line_df[x_col] = pd.to_datetime(line_df[x_col], errors='coerce')
            line_df = line_df.dropna(subset=[x_col]).sort_values(by=x_col)

        fig = px.line(
            line_df,
            x=x_col,
            y=y_col,
            color=group_col if has_grp else None,
            title=f"Custom Trend Chart: {y_col} across {x_col}",
            markers=True,
            color_discrete_sequence=palette
        )
        apply_chart_theme(fig, f"Custom Trend Chart: {y_col} across {x_col}", theme_mode=theme_mode)
        fig.update_traces(line=dict(width=2.5))

    # 3. Scatter Plot
    elif chart_type_clean in ["Scatter Plot", "Scatter"]:
        if not x_col or not y_col:
            raise ChartValidationError("Scatter plots require choosing two numerical columns (X and Y).")
        if (x_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[x_col])) or \
           (y_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[y_col])):
            raise ChartValidationError(f"Both X Axis ('{x_col}') and Y Axis ('{y_col}') must be numeric for Scatter Plot.")

        has_grp = group_col and group_col != "None" and group_col in df.columns
        fig = px.scatter(
            plot_df,
            x=x_col,
            y=y_col,
            color=group_col if has_grp else None,
            title=f"Custom Scatter Plot: {x_col} vs {y_col}",
            color_discrete_sequence=palette,
            opacity=0.85
        )
        apply_chart_theme(fig, f"Custom Scatter Plot: {x_col} vs {y_col}", theme_mode=theme_mode)
        fig.update_traces(marker=dict(size=7))

    # 4. Box Plot
    elif chart_type_clean in ["Box Plot", "Box"]:
        if not y_col:
            raise ChartValidationError("Box plot requires a numerical metric for the Y Axis.")
        if y_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[y_col]):
            raise ChartValidationError(f"Y Axis ('{y_col}') must be numerical for a Box Plot.")

        fig = px.box(
            plot_df,
            x=x_col if x_col and x_col in df.columns else None,
            y=y_col,
            color=group_col if group_col and group_col != "None" and group_col in df.columns else None,
            title=f"Custom Box Distribution: {y_col}" + (f" by {x_col}" if x_col else ""),
            color_discrete_sequence=palette
        )
        apply_chart_theme(fig, f"Custom Box Distribution: {y_col}" + (f" by {x_col}" if x_col else ""), theme_mode=theme_mode)

    # 5. Histogram
    elif chart_type_clean in ["Histogram"]:
        target = x_col or y_col
        if not target:
            raise ChartValidationError("Histogram requires at least one column specified.")

        has_grp = group_col and group_col != "None" and group_col in df.columns
        fig = px.histogram(
            plot_df,
            x=target,
            color=group_col if has_grp else None,
            nbins=30,
            marginal="rug",
            title=f"Custom Frequency Histogram: {target}",
            color_discrete_sequence=palette,
            barmode="overlay" if has_grp else "relative"
        )
        apply_chart_theme(fig, f"Custom Frequency Histogram: {target}", theme_mode=theme_mode)

    # 6. Pie / Donut Chart
    elif chart_type_clean in ["Pie Chart", "Pie", "Donut Chart"]:
        cat = x_col or (profile.categorical_columns[0] if profile.categorical_columns else None)
        val = y_col if (y_col and y_col in profile.numerical_columns) else None

        if not cat:
            raise ChartValidationError("Pie charts require a categorical column for slices.")

        pie_df = plot_df.groupby(cat)[val].sum().reset_index() if val else plot_df[cat].value_counts().reset_index()
        pie_df.columns = [cat, 'value']
        pie_df = pie_df.head(10)

        fig = px.pie(
            pie_df,
            names=cat,
            values='value',
            hole=0.45 if "Donut" in chart_type_clean else 0.0,
            title=f"Custom Proportional Distribution: {cat}",
            color_discrete_sequence=palette
        )
        apply_chart_theme(fig, f"Custom Proportional Distribution: {cat}", theme_mode=theme_mode)

    else:
        raise ChartValidationError(f"Unsupported chart type '{chart_type}'. Choose from: Bar, Line, Scatter, Box, Histogram, Pie.")

    return VisualizationResult(
        chart_id=f"custom_{chart_type_clean.lower().replace(' ', '_')}",
        title=f"Custom {chart_type_clean}: {x_col or ''} vs {y_col or ''}",
        chart_type=chart_type_clean,
        plotly_json=fig.to_json(),
        description=f"User customized {chart_type_clean} visualization.",
        reason=f"Custom visualization for {x_col} and {y_col}.",
        domain_relevance="User visual builder.",
        columns_used=[c for c in [x_col, y_col, group_col] if c and c != "None" and c in df.columns],
        key_takeaway=f"Custom visual examination of {', '.join([c for c in [x_col, y_col] if c])}.",
        analytical_question=f"User-specified {chart_type_clean} visualization."
    )
