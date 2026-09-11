# DataCleaning4U System Architecture

## Pipeline Overview

```
User Input
   │
   ├── Domain Selection (Sales & Retail / Finance / Healthcare / HR)
   └── File Upload (CSV / XLSX)
         │
         ▼
 1. Ingestion Engine (`ingestion/loader.py`)
         │  - Encoding detection (UTF-8, Latin-1, CP1252)
         │  - Multi-sheet Excel inspection & selection
         │  - Raw file preservation (creates working copy)
         ▼
 2. Dataset Profiler (`profiling/profiler.py`)
         │  - Column taxonomy classification (Numerical, Categorical, Datetime, Boolean, ID)
         │  - Per-column missing stats, uniqueness, sample records
         ▼
 3. Cleaning Engine (`cleaning/cleaner.py`)
         │  - Text standardization & whitespace trimming
         │  - Safe datatype conversion (numeric/datetime)
         │  - Duplicate row removal & reporting
         │  - Smart missing value imputation (median / mode / preserved dates)
         │  - Statistical outlier flagging (IQR, Z-Score)
         ▼
 4. Statistical & Anomaly Engine (`analysis/`)
         │  - Numerical stats (quartiles, std, sum, min, max)
         │  - Categorical frequencies & percentages
         │  - Group aggregations & trend detection
         │  - Multi-dimensional Isolation Forest anomaly detection
         ▼
 5. Visualization Engine (`visualization/`)
         │  - Automatic Plotly chart selection (Line, Bar, Scatter, Histogram, Box, Heatmap)
         │  - User-Selected Interactive Chart Builder with validation
         ▼
 6. Report & Export Center (`reports/`)
         │  - Non-AI deterministic executive summary
         │  - Cleaned CSV & XLSX downloads
         │  - Standalone HTML & ReportLab PDF exports
```
