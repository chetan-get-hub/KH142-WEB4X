from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from models.result_models import ColumnProfile, DatasetProfile
from config.settings import DOMAIN_KEYWORDS

def profile_dataset(
    df: pd.DataFrame,
    file_name: str = "dataset.csv",
    file_type: str = "CSV",
    file_size_bytes: Optional[int] = None,
    domain: Optional[str] = None
) -> DatasetProfile:
    """
    Profiles a DataFrame with deep structural understanding, column roles,
    cardinality assessment, and analytical suitability evaluation.
    """
    total_rows = len(df)
    total_cols = len(df.columns)
    column_profiles: Dict[str, ColumnProfile] = {}

    num_cols: List[str] = []
    cat_cols: List[str] = []
    dt_cols: List[str] = []
    bool_cols: List[str] = []
    id_cols: List[str] = []

    domain_hints = DOMAIN_KEYWORDS.get(domain, {}) if domain else {}
    metric_keywords = [k.lower() for k in domain_hints.get("metrics", [])]
    group_keywords = [k.lower() for k in domain_hints.get("groups", [])]
    time_keywords = [k.lower() for k in domain_hints.get("time", [])]
    id_keywords = [k.lower() for k in domain_hints.get("id", [])]

    for col in df.columns:
        series = df[col]
        raw_dtype_str = str(series.dtype)
        col_clean = str(col).lower().replace("_", "").replace(" ", "").replace("-", "")

        # Missing stats
        missing_cnt = int(series.isna().sum())
        missing_pct = round((missing_cnt / total_rows * 100), 2) if total_rows > 0 else 0.0

        # Non-null values for inspection
        non_null_series = series.dropna()
        unique_cnt = int(non_null_series.nunique())

        # Cardinality calculation
        if unique_cnt <= 10:
            cardinality = "low"
        elif unique_cnt <= 100:
            cardinality = "medium"
        else:
            cardinality = "high"

        # Sample values
        samples = non_null_series.head(5).tolist()
        samples = [
            x.item() if hasattr(x, "item") else str(x) if isinstance(x, (pd.Timestamp, np.datetime64)) else x
            for x in samples
        ]

        inferred_type = 'categorical'
        role = 'general'
        col_stats: Dict[str, Any] = {}
        suitable_group = False
        suitable_measure = False
        suitable_time = False

        # 1. Identifier Detection
        is_named_id = any(k in col_clean for k in ['id', 'uuid', 'code', 'key', 'pk', 'number', 'accountno', 'empid', 'patientid']) or col_clean in id_keywords
        if is_named_id and (unique_cnt >= max(1, int(total_rows * 0.8)) or (total_rows <= 15 and unique_cnt >= total_rows - 2)):
            inferred_type = 'identifier'
            role = 'identifier'
            id_cols.append(col)

        # 2. Boolean Detection
        elif pd.api.types.is_bool_dtype(series) or (
            unique_cnt <= 2 and set(non_null_series.astype(str).str.lower().unique()).issubset(
                {'true', 'false', '0', '1', 't', 'f', 'y', 'n', 'yes', 'no'}
            )
        ):
            inferred_type = 'boolean'
            role = 'grouping'
            suitable_group = True
            bool_cols.append(col)

        # 3. Numeric Detection
        elif pd.api.types.is_numeric_dtype(series):
            inferred_type = 'numerical'
            role = 'measurement'
            suitable_measure = True
            num_cols.append(col)

            # Low cardinality integers might also serve as grouping (e.g. rating 1-5, year, status code)
            if unique_cnt <= 8:
                suitable_group = True

            if not non_null_series.empty:
                val_min = float(non_null_series.min())
                val_max = float(non_null_series.max())
                val_mean = float(non_null_series.mean())
                val_median = float(non_null_series.median())
                val_std = float(non_null_series.std()) if len(non_null_series) > 1 else 0.0
                val_var = float(non_null_series.var()) if len(non_null_series) > 1 else 0.0
                q25 = float(non_null_series.quantile(0.25))
                q75 = float(non_null_series.quantile(0.75))
                iqr = round(q75 - q25, 4)
                cv = round((val_std / val_mean * 100), 2) if val_mean != 0 else 0.0

                col_stats = {
                    "min": round(val_min, 4),
                    "max": round(val_max, 4),
                    "mean": round(val_mean, 4),
                    "median": round(val_median, 4),
                    "std": round(val_std, 4),
                    "variance": round(val_var, 4),
                    "q25": round(q25, 4),
                    "q75": round(q75, 4),
                    "iqr": iqr,
                    "cv_percent": cv,
                    "zeros_count": int((non_null_series == 0).sum()),
                    "negative_count": int((non_null_series < 0).sum())
                }

        # 4. Datetime Detection
        elif pd.api.types.is_datetime64_any_dtype(series):
            inferred_type = 'datetime'
            role = 'temporal'
            suitable_time = True
            dt_cols.append(col)
            if not non_null_series.empty:
                col_stats = {
                    "min": str(non_null_series.min()),
                    "max": str(non_null_series.max())
                }

        # 5. String / Object Column Analysis
        else:
            is_dt_candidate = any(k in col_clean for k in ['date', 'time', 'month', 'year', 'day']) or col_clean in time_keywords
            parsed_dt_success = False
            if is_dt_candidate and not non_null_series.empty:
                try:
                    parsed_dt = pd.to_datetime(non_null_series.head(50), format='mixed', errors='coerce')
                    if parsed_dt.notna().sum() / len(parsed_dt) > 0.75:
                        inferred_type = 'datetime'
                        role = 'temporal'
                        suitable_time = True
                        dt_cols.append(col)
                        parsed_dt_success = True
                        col_stats = {
                            "min": str(parsed_dt.min()),
                            "max": str(parsed_dt.max())
                        }
                except Exception:
                    pass

            if not parsed_dt_success:
                inferred_type = 'categorical'
                role = 'grouping' if unique_cnt <= 50 else 'general'
                suitable_group = unique_cnt <= 50
                cat_cols.append(col)

        # Domain keyword alignment
        if any(m in col_clean for m in metric_keywords) and inferred_type == 'numerical':
            role = 'measurement'
            suitable_measure = True
        if any(g in col_clean for g in group_keywords) and inferred_type in ['categorical', 'boolean']:
            role = 'grouping'
            suitable_group = True

        column_profiles[col] = ColumnProfile(
            name=col,
            inferred_type=inferred_type,
            raw_dtype=raw_dtype_str,
            missing_count=missing_cnt,
            missing_percentage=missing_pct,
            unique_count=unique_cnt,
            sample_values=samples,
            stats=col_stats,
            role=role,
            cardinality=cardinality,
            suitable_for_grouping=suitable_group,
            suitable_for_measurement=suitable_measure,
            suitable_for_timeseries=suitable_time
        )

    dup_count = int(df.duplicated().sum()) if total_rows > 0 else 0

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
        identifier_columns=id_cols,
        domain_hint=domain,
        duplicate_count=dup_count
    )
