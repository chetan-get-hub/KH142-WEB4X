from typing import Optional, List
import pandas as pd
import numpy as np
import plotly.express as px
from models.result_models import VisualizationResult, DatasetProfile

class ChartValidationError(Exception):
    """Exception raised when user selected chart parameters are invalid or incompatible."""
    pass

def build_custom_visualization(
    df: pd.DataFrame,
    profile: DatasetProfile,
    chart_type: str,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    group_col: Optional[str] = None
) -> VisualizationResult:
    """
    Builds a custom user-requested chart with strict parameter validation,
    meaningful error messages, and robust layout styling.
    """
    if df.empty:
        raise ChartValidationError("Cannot generate chart from an empty dataset.")

    # Downsample for visualization rendering if dataset is huge
    MAX_POINTS = 5000
    plot_df = df.sample(MAX_POINTS, random_state=42) if len(df) > MAX_POINTS else df.copy()

    color_palette = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#3B82F6']
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
            color_discrete_sequence=color_palette,
            text_auto='.2s'
        )

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
            line_df = line_df.dropna().sort_values(by=x_col)

        fig = px.line(
            line_df,
            x=x_col,
            y=y_col,
            color=group_col if has_grp else None,
            markers=True,
            title=f"Custom Line Chart: {y_col} vs {x_col}",
            color_discrete_sequence=color_palette
        )

    # 3. Scatter Plot
    elif chart_type_clean in ["Scatter Plot", "Scatter"]:
        if not x_col or not y_col:
            raise ChartValidationError("Scatter plots require selecting both X Axis and Y Axis columns.")
        if x_col not in profile.numerical_columns or y_col not in profile.numerical_columns:
            raise ChartValidationError(f"Scatter plots require two numerical columns. '{x_col}' or '{y_col}' is not numerical.")

        has_grp = group_col and group_col != "None" and group_col in df.columns
        fig = px.scatter(
            plot_df,
            x=x_col,
            y=y_col,
            color=group_col if has_grp else None,
            title=f"Custom Scatter Plot: {y_col} vs {x_col}",
            color_discrete_sequence=color_palette
        )

    # 4. Histogram
    elif chart_type_clean in ["Histogram"]:
        target_col = x_col if x_col and x_col != "None" else y_col
        if not target_col or target_col == "None":
            raise ChartValidationError("Histogram requires selecting a target column (X or Y Axis).")
        if target_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[target_col]):
            raise ChartValidationError(f"Histogram requires a numerical column. Column '{target_col}' is not numerical.")

        has_grp = group_col and group_col != "None" and group_col in df.columns
        fig = px.histogram(
            plot_df,
            x=target_col,
            color=group_col if has_grp else None,
            nbins=25,
            title=f"Custom Histogram: Distribution of {target_col}",
            color_discrete_sequence=color_palette
        )

    # 5. Box Plot
    elif chart_type_clean in ["Box Plot", "Box"]:
        num_target = y_col if (y_col and y_col != "None" and y_col in profile.numerical_columns) else (x_col if (x_col and x_col != "None" and x_col in profile.numerical_columns) else None)
        if not num_target:
            raise ChartValidationError("Box Plot requires selecting at least one numerical column (on X or Y Axis).")

        cat_target = x_col if (x_col and x_col != num_target and x_col != "None") else (group_col if group_col and group_col != "None" else None)

        fig = px.box(
            plot_df,
            y=num_target,
            x=cat_target,
            color=cat_target if cat_target else None,
            title=f"Custom Box Plot: Spread of {num_target}",
            color_discrete_sequence=color_palette,
            points="all"
        )

    # 6. Pie / Donut Chart
    elif chart_type_clean in ["Pie Chart", "Pie"]:
        if not x_col or not y_col or x_col == "None" or y_col == "None":
            raise ChartValidationError("Pie chart requires a Categorical column (X Axis) and a Numerical Metric (Y Axis).")
        if y_col not in profile.numerical_columns and not pd.api.types.is_numeric_dtype(df[y_col]):
            raise ChartValidationError(f"Y Axis for Pie Chart must be a numerical metric. Column '{y_col}' is not numerical.")

        grouped = plot_df.groupby(x_col, as_index=False)[y_col].sum().head(10)

        fig = px.pie(
            grouped,
            names=x_col,
            values=y_col,
            hole=0.35,  # Donut style for modern appearance
            title=f"Custom Donut Chart: Proportion of {y_col} by {x_col}",
            color_discrete_sequence=color_palette
        )

    # 7. Correlation Heatmap
    elif chart_type_clean in ["Heatmap", "Correlation Heatmap"]:
        num_df = plot_df[profile.numerical_columns].select_dtypes(include=[np.number])
        if num_df.shape[1] < 2:
            raise ChartValidationError("Correlation Heatmap requires at least two numerical columns in the dataset.")

        corr_matrix = num_df.corr().round(2)
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1.0,
            zmax=1.0,
            title="Custom Correlation Heatmap"
        )

    else:
        raise ChartValidationError(f"Unsupported chart type: '{chart_type}'. Choose from Bar, Line, Scatter, Histogram, Box, Pie, Heatmap.")

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40)
    )

    return VisualizationResult(
        chart_id=f"custom_{chart_type_clean.lower().replace(' ', '_')}",
        title=f"User-Generated {chart_type_clean}",
        chart_type=chart_type_clean,
        plotly_json=fig.to_json(),
        description=f"User-configured {chart_type_clean} plotting {y_col or 'N/A'} against {x_col or 'N/A'}.",
        columns_used=[c for c in [x_col, y_col, group_col] if c and c != "None"],
        reason="Generated via interactive custom chart builder.",
        domain_relevance="User customized exploratory view."
    )
