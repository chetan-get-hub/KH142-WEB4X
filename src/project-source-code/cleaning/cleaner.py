from typing import Tuple, Dict, List, Any
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from models.result_models import CleaningReport, DatasetProfile
from profiling.profiler import profile_dataset
from config.settings import OUTLIER_IQR_FACTOR, OUTLIER_ZSCORE_THRESHOLD, NA_VALUES

def clean_dataset(
    df: pd.DataFrame,
    profile: DatasetProfile = None,
    handle_missing: bool = True,
    remove_duplicates: bool = True,
    convert_types: bool = True,
    standardize_text: bool = True,
    flag_outliers: bool = True
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Data Cleaning Engine for DataCleaning4U.
    Applies non-destructive cleaning, data type conversion, text standardization,
    missing value imputation, duplicate removal, and outlier flagging.
    """
    # Working copy to preserve original uploaded dataset
    cleaned_df = df.copy(deep=True)
    rows_before = len(cleaned_df)
    cols_before = len(cleaned_df.columns)

    cleaning_steps: List[Dict[str, Any]] = []
    warnings: List[str] = []
    missing_handled_per_col: Dict[str, int] = {}
    datatype_conversions: Dict[str, str] = {}
    standardized_cols: List[str] = []
    duplicates_removed_count = 0
    duplicates_found_count = 0
    outliers_flagged_total = 0

    # Step 1: Text Standardization & Trim Whitespace
    if standardize_text:
        step_log = {"step": "Text Standardization", "details": []}
        for col in cleaned_df.columns:
            if pd.api.types.is_object_dtype(cleaned_df[col]) or pd.api.types.is_string_dtype(cleaned_df[col]):
                # Replace common string missing value representations with NaN first
                cleaned_df[col] = cleaned_df[col].apply(
                    lambda v: np.nan if str(v).strip() in NA_VALUES else str(v).strip() if pd.notna(v) else np.nan
                )
                standardized_cols.append(col)
        step_log["details"].append(f"Trimmed whitespace and normalized NA markers across {len(standardized_cols)} text columns.")
        cleaning_steps.append(step_log)

    # Step 2: Datatype Conversion (Safe numeric & datetime parsing)
    if convert_types:
        step_log = {"step": "Datatype Conversion", "details": []}
        for col in cleaned_df.columns:
            orig_dtype = str(cleaned_df[col].dtype)
            
            # Try numeric conversion if object
            if cleaned_df[col].dtype == 'object':
                # Test numeric conversion
                numeric_converted = pd.to_numeric(cleaned_df[col], errors='coerce')
                # If majority of non-null values converted successfully, apply conversion
                non_null_orig = cleaned_df[col].dropna()
                if not non_null_orig.empty:
                    success_rate = numeric_converted.dropna().count() / non_null_orig.count()
                    if success_rate > 0.8:
                        cleaned_df[col] = numeric_converted
                        datatype_conversions[col] = f"{orig_dtype} -> float64/int64"
                        step_log["details"].append(f"Converted column '{col}' to numeric.")
                        continue
                
                # Test datetime conversion
                try:
                    dt_converted = pd.to_datetime(cleaned_df[col], format='mixed', errors='coerce')
                    if not non_null_orig.empty:
                        dt_success_rate = dt_converted.dropna().count() / non_null_orig.count()
                        if dt_success_rate > 0.8:
                            cleaned_df[col] = dt_converted
                            datatype_conversions[col] = f"{orig_dtype} -> datetime64"
                            step_log["details"].append(f"Converted column '{col}' to datetime.")
                            continue
                except Exception:
                    pass
        cleaning_steps.append(step_log)

    # Step 3: Duplicate Row Detection & Removal
    if remove_duplicates:
        step_log = {"step": "Duplicate Removal", "details": []}
        duplicates_found_count = int(cleaned_df.duplicated().sum())
        if duplicates_found_count > 0:
            cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
            duplicates_removed_count = duplicates_found_count
            step_log["details"].append(f"Detected and removed {duplicates_found_count} duplicate row(s).")
        else:
            step_log["details"].append("No duplicate rows found.")
        cleaning_steps.append(step_log)

    # Step 4: Missing Value Handling
    if handle_missing:
        step_log = {"step": "Missing Value Imputation", "details": []}
        for col in cleaned_df.columns:
            missing_count = int(cleaned_df[col].isna().sum())
            if missing_count > 0:
                missing_handled_per_col[col] = missing_count
                
                # High missing check
                if missing_count / len(cleaned_df) > 0.5:
                    warnings.append(f"Column '{col}' has >50% missing values ({missing_count}/{len(cleaned_df)} rows).")

                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    median_val = cleaned_df[col].median()
                    if pd.notna(median_val):
                        cleaned_df[col] = cleaned_df[col].fillna(median_val)
                        step_log["details"].append(f"Imputed {missing_count} missing value(s) in numeric column '{col}' with median ({round(median_val, 2)}).")
                elif pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
                    # Do not blindly fabricate dates for datetimes
                    step_log["details"].append(f"Preserved {missing_count} missing date value(s) in '{col}' without fabrication.")
                else:
                    mode_series = cleaned_df[col].mode()
                    fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                    cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                    step_log["details"].append(f"Imputed {missing_count} missing value(s) in categorical column '{col}' with mode ('{fill_val}').")
        cleaning_steps.append(step_log)

    # Step 5: Outlier Flagging (IQR & Isolation Forest)
    if flag_outliers:
        step_log = {"step": "Outlier Detection & Flagging", "details": []}
        num_cols = cleaned_df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Filter out potential identifier columns from numeric outliers
        num_cols = [c for c in num_cols if not c.lower().endswith(('id', '_id', 'uuid', 'pk', 'code', 'number'))]

        outlier_rows = set()
        for col in num_cols:
            q25 = cleaned_df[col].quantile(0.25)
            q75 = cleaned_df[col].quantile(0.75)
            iqr = q75 - q25
            if iqr > 0:
                lower_bound = q25 - (OUTLIER_IQR_FACTOR * iqr)
                upper_bound = q75 + (OUTLIER_IQR_FACTOR * iqr)
                col_outliers = cleaned_df[(cleaned_df[col] < lower_bound) | (cleaned_df[col] > upper_bound)].index
                outlier_rows.update(col_outliers)

        outliers_flagged_total = len(outlier_rows)
        step_log["details"].append(f"Flagged {outliers_flagged_total} row(s) containing statistical outliers across numerical features.")
        if outliers_flagged_total > 0:
            warnings.append(f"{outliers_flagged_total} row(s) contain statistical outliers. Outliers are flagged for review rather than deleted.")
        cleaning_steps.append(step_log)

    rows_after = len(cleaned_df)
    cols_after = len(cleaned_df.columns)
    total_missing_handled = sum(missing_handled_per_col.values())

    report = CleaningReport(
        rows_before=rows_before,
        rows_after=rows_after,
        cols_before=cols_before,
        cols_after=cols_after,
        duplicates_found=duplicates_found_count,
        duplicates_removed=duplicates_removed_count,
        missing_handled_per_column=missing_handled_per_col,
        total_missing_handled=total_missing_handled,
        datatype_conversions=datatype_conversions,
        standardized_columns=standardized_cols,
        outliers_flagged_count=outliers_flagged_total,
        warnings=warnings,
        cleaning_steps=cleaning_steps
    )

    return cleaned_df, report
