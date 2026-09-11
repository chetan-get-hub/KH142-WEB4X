from typing import Dict, List, Any
import pandas as pd
import numpy as np
from models.result_models import ColumnProfile, DatasetProfile

def profile_dataset(
    df: pd.DataFrame,
    file_name: str = "dataset.csv",
    file_type: str = "CSV",
    file_size_bytes: int = None
) -> DatasetProfile:
    """
    Profiles a DataFrame and returns a structured DatasetProfile object.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    column_profiles: Dict[str, ColumnProfile] = {}

    num_cols: List[str] = []
    cat_cols: List[str] = []
    dt_cols: List[str] = []
    bool_cols: List[str] = []
    id_cols: List[str] = []

    for col in df.columns:
        series = df[col]
        raw_dtype_str = str(series.dtype)
        
        # Missing stats
        missing_cnt = int(series.isna().sum())
        missing_pct = round((missing_cnt / total_rows * 100), 2) if total_rows > 0 else 0.0

        # Non-null values for inspection
        non_null_series = series.dropna()
        unique_cnt = int(non_null_series.nunique())
        
        # Sample non-null values
        samples = non_null_series.head(5).tolist()
        # Convert numpy types to python native types for json safety
        samples = [x.item() if hasattr(x, "item") else str(x) if isinstance(x, (pd.Timestamp, np.datetime64)) else x for x in samples]

        inferred_type = 'categorical'
        col_stats: Dict[str, Any] = {}

        # 1. Check for identifier
        col_lower = str(col).lower()
        if (col_lower.endswith(('id', '_id', 'uuid', 'code', 'key', 'pk', 'number')) or col_lower in ['id', 'patientid', 'empid', 'transactionid']) and unique_cnt >= max(1, int(total_rows * 0.9)):
            inferred_type = 'identifier'
            id_cols.append(col)
        # 2. Check for Boolean
        elif pd.api.types.is_bool_dtype(series) or (unique_cnt <= 2 and set(non_null_series.unique()).issubset({True, False, 0, 1, 'True', 'False', 'true', 'false', 'T', 'F', 'Y', 'N', '1', '0'})):
            inferred_type = 'boolean'
            bool_cols.append(col)
        # 3. Check for Numeric
        elif pd.api.types.is_numeric_dtype(series):
            # If low cardinality (e.g. rating 1-5 or zip code), might still be numeric for stats
            inferred_type = 'numerical'
            num_cols.append(col)
            if not non_null_series.empty:
                col_stats = {
                    "min": float(non_null_series.min()),
                    "max": float(non_null_series.max()),
                    "mean": float(non_null_series.mean()),
                    "median": float(non_null_series.median()),
                    "std": float(non_null_series.std()) if len(non_null_series) > 1 else 0.0,
                    "q25": float(non_null_series.quantile(0.25)),
                    "q75": float(non_null_series.quantile(0.75))
                }
        # 4. Check Datetime
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred_type = 'datetime'
            dt_cols.append(col)
            if not non_null_series.empty:
                col_stats = {
                    "min": str(non_null_series.min()),
                    "max": str(non_null_series.max())
                }
        else:
            # Try to test if string column is parseable as datetime
            if non_null_series.dtype == 'object':
                try:
                    parsed_dt = pd.to_datetime(non_null_series.head(50), format='mixed', errors='coerce')
                    if parsed_dt.notna().sum() / len(parsed_dt) > 0.8:
                        inferred_type = 'datetime'
                        dt_cols.append(col)
                        col_stats = {
                            "min": str(parsed_dt.min()),
                            "max": str(parsed_dt.max())
                        }
                    else:
                        inferred_type = 'categorical'
                        cat_cols.append(col)
                except Exception:
                    inferred_type = 'categorical'
                    cat_cols.append(col)
            else:
                inferred_type = 'categorical'
                cat_cols.append(col)

        column_profiles[col] = ColumnProfile(
            name=col,
            inferred_type=inferred_type,
            raw_dtype=raw_dtype_str,
            missing_count=missing_cnt,
            missing_percentage=missing_pct,
            unique_count=unique_cnt,
            sample_values=samples,
            stats=col_stats
        )

    return DatasetProfile(
        total_rows=total_rows,
        total_columns=total_cols,
        file_name=file_name,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        columns=column_profiles,
        numerical_columns=num_cols,
        categorical_columns=cat_cols,
        datetime_columns=dt_cols,
        boolean_columns=bool_cols,
        identifier_columns=id_cols
    )
