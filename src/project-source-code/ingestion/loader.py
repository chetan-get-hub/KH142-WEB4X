import io
import os
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
from config.settings import NA_VALUES

class DatasetIngestionError(Exception):
    """Custom exception for file loading errors."""
    pass

def inspect_excel_sheets(file_source: Any) -> List[str]:
    """
    Given a file path or file-like object, return a list of sheet names in the Excel file.
    """
    try:
        if isinstance(file_source, (str, os.PathLike)):
            excel_file = pd.ExcelFile(file_source)
            return excel_file.sheet_names
        elif hasattr(file_source, "read"):
            # File-like object (e.g. Streamlit UploadedFile)
            content = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            excel_file = pd.ExcelFile(io.BytesIO(content))
            return excel_file.sheet_names
        else:
            raise DatasetIngestionError("Unsupported file source for Excel inspection.")
    except Exception as e:
        raise DatasetIngestionError(f"Could not inspect Excel sheets: {str(e)}")

def load_dataset(
    file_source: Any,
    filename: str,
    sheet_name: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Safely load a CSV or XLSX dataset into a Pandas DataFrame.
    Returns (working_df_copy, metadata_dict).
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ['.csv', '.xlsx', '.xls']:
        raise DatasetIngestionError("Unsupported file format. Please upload a CSV or XLSX file.")

    raw_bytes = None
    file_size = None

    if isinstance(file_source, (str, os.PathLike)):
        if not os.path.exists(file_source):
            raise DatasetIngestionError(f"File not found: {file_source}")
        file_size = os.path.getsize(file_source)
    elif hasattr(file_source, "read"):
        raw_bytes = file_source.read()
        file_size = len(raw_bytes)
        if hasattr(file_source, "seek"):
            file_source.seek(0)
    else:
        raise DatasetIngestionError("Invalid file input provided.")

    if file_size == 0:
        raise DatasetIngestionError("The uploaded file is empty (0 bytes).")

    df: Optional[pd.DataFrame] = None

    if ext == '.csv':
        encodings_to_try = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        last_error = None

        for enc in encodings_to_try:
            try:
                if raw_bytes is not None:
                    buffer = io.BytesIO(raw_bytes)
                    df = pd.read_csv(buffer, encoding=enc, na_values=NA_VALUES, keep_default_na=True)
                else:
                    df = pd.read_csv(file_source, encoding=enc, na_values=NA_VALUES, keep_default_na=True)
                break
            except Exception as e:
                last_error = e

        if df is None:
            raise DatasetIngestionError(f"Failed to parse CSV file: {str(last_error)}")

    elif ext in ['.xlsx', '.xls']:
        try:
            if raw_bytes is not None:
                buffer = io.BytesIO(raw_bytes)
                xl = pd.ExcelFile(buffer)
                target_sheet = sheet_name if sheet_name and sheet_name in xl.sheet_names else xl.sheet_names[0]
                df = pd.read_excel(xl, sheet_name=target_sheet, na_values=NA_VALUES, keep_default_na=True)
            else:
                xl = pd.ExcelFile(file_source)
                target_sheet = sheet_name if sheet_name and sheet_name in xl.sheet_names else xl.sheet_names[0]
                df = pd.read_excel(xl, sheet_name=target_sheet, na_values=NA_VALUES, keep_default_na=True)
        except Exception as e:
            raise DatasetIngestionError(f"Failed to parse Excel file: {str(e)}")

    if df is None or df.empty:
        raise DatasetIngestionError("The uploaded dataset contains no usable rows or columns.")

    # Strip whitespace from column names if present
    df.columns = [str(col).strip() if isinstance(col, str) else str(col) for col in df.columns]

    metadata = {
        "file_name": filename,
        "file_type": ext.upper().replace('.', ''),
        "file_size_bytes": file_size,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "sheet_name": sheet_name
    }

    # Return a deep copy so original is preserved
    return df.copy(deep=True), metadata
