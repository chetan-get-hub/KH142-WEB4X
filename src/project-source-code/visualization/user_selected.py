from typing import Optional, List
import pandas as pd
import numpy as np
import plotly.express as px
from models.result_models import VisualizationResult, DatasetProfile

class ChartValidationError(Exception):
    """Exception raised when selected chart parameters are invalid."""
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
    Builds a custom user-requested chart with strict parameter validation.
    """
    color_seq = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4']

    chart_type_clean = chart_type.strip().title()

    if chart_type_clean in ["Bar Chart", "Bar"]:
        if not x_col or not y_col:
            raise ChartValidationError("Bar charts require selecting both X Axis and Y Axis columns.")
        if y_col not in profile.numerical_columns:
            raise ChartValidationError(f"Y Axis for Bar Chart should be numerical. Column '{y_col}' is not numerical.")

        grouped = df.groupby([x_col] + ([group_col] if group_col and group_col != "None" else []), as_index=False)[y_col].agg('sum')
        grouped = grouped.head(30)

        fig = px.bar(
            grouped,
            x=x_col,
            y=y_col,
            color=group_col if group_col and group_col != "None" else x_col,
            barmode="group" if group_col and group_col != "None" else "relative",
            title=f"Custom Bar Chart: {y_col} by {x_col}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Line Chart", "Line"]:
        if not x_col or not y_col:
            raise ChartValidationError("Line charts require selecting both X Axis and Y Axis columns.")
        if y_col not in profile.numerical_columns:
            raise ChartValidationError(f"Y Axis for Line Chart should be numerical. Column '{y_col}' is not numerical.")

        plot_df = df[[x_col, y_col] + ([group_col] if group_col and group_col != "None" else [])].dropna().copy()
        
        # If X is datetime string, attempt parse & sort
        if x_col in profile.datetime_columns or pd.api.types.is_datetime64_any_dtype(plot_df[x_col]):
            plot_df[x_col] = pd.to_datetime(plot_df[x_col], errors='coerce')
            plot_df = plot_df.dropna().sort_values(by=x_col)

        fig = px.line(
            plot_df,
            x=x_col,
            y=y_col,
            color=group_col if group_col and group_col != "None" else None,
            markers=True,
            title=f"Custom Line Chart: {y_col} vs {x_col}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Scatter Plot", "Scatter"]:
        if not x_col or not y_col:
            raise ChartValidationError("Scatter plots require selecting both X Axis and Y Axis columns.")
        if x_col not in profile.numerical_columns or y_col not in profile.numerical_columns:
            raise ChartValidationError(f"Scatter plots require two numerical columns. '{x_col}' or '{y_col}' is not numerical.")

        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=group_col if group_col and group_col != "None" else None,
            title=f"Custom Scatter Plot: {y_col} vs {x_col}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Histogram"]:
        target_col = x_col if x_col else y_col
        if not target_col:
            raise ChartValidationError("Histogram requires selecting a target column (X or Y Axis).")
        if target_col not in profile.numerical_columns:
            raise ChartValidationError(f"Histogram requires a numerical column. Column '{target_col}' is not numerical.")

        fig = px.histogram(
            df,
            x=target_col,
            color=group_col if group_col and group_col != "None" else None,
            title=f"Custom Histogram: Distribution of {target_col}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Box Plot", "Box"]:
        num_target = y_col if y_col and y_col in profile.numerical_columns else (x_col if x_col and x_col in profile.numerical_columns else None)
        if not num_target:
            raise ChartValidationError("Box Plot requires selecting a numerical column.")

        cat_target = x_col if (x_col and x_col != num_target) else (group_col if group_col and group_col != "None" else None)

        fig = px.box(
            df,
            y=num_target,
            x=cat_target,
            color=group_col if group_col and group_col != "None" else cat_target,
            title=f"Custom Box Plot: Spread of {num_target}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Pie Chart", "Pie"]:
        if not x_col or not y_col:
            raise ChartValidationError("Pie chart requires a Categorical column (X Axis) and a Numerical Metric (Y Axis).")
        if y_col not in profile.numerical_columns:
            raise ChartValidationError(f"Y Axis for Pie Chart should be a numerical metric. Column '{y_col}' is not numerical.")

        grouped = df.groupby(x_col, as_index=False)[y_col].sum().head(10)

        fig = px.pie(
            grouped,
            names=x_col,
            values=y_col,
            title=f"Custom Pie Chart: Proportion of {y_col} by {x_col}",
            color_discrete_sequence=color_seq
        )

    elif chart_type_clean in ["Heatmap"]:
        num_df = df[profile.numerical_columns].select_dtypes(include=[np.number])
        if num_df.shape[1] < 2:
            raise ChartValidationError("Correlation Heatmap requires at least two numerical columns in the dataset.")

        corr_matrix = num_df.corr().round(2)
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Viridis",
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
        description=f"User customized {chart_type_clean} plotting {y_col or 'N/A'} against {x_col or 'N/A'}."
    )
