# DataCleaning4U 

> **From raw data to useful insights.**

DataCleaning4U is an autonomous data analyst agent for CSV and XLSX datasets built with Python, Pandas, Scikit-learn, Plotly, and Streamlit. It delivers an end-to-end dataset profiling, non-destructive data cleaning, statistical analysis, multi-method anomaly detection, automatic & custom interactive visualizations, executive summary generation, and multi-format report exports—all without relying on external LLM or AI APIs.

---

## 🌟 Core Features

1. **Multi-Domain Context Support**:
   - 🛒 *Sales & Retail*: Revenue, orders, category performance, customer metrics.
   - 🏦 *Finance & Banking*: Account balances, transaction types, credit scores, fraud indicators.
   - 🏥 *Healthcare*: Patient demographics, clinical readings, treatment costs, stay duration.
   - 👥 *Human Resources (HR)*: Employee compensation, performance ratings, experience, attrition risk.

2. **File Ingestion Engine**:
   - Supports `.csv`, `.xlsx`, and `.xls` files.
   - Multi-sheet Excel workbook inspection & selection.
   - Safe encoding detection (`utf-8`, `latin1`, `cp1252`).
   - Preservation of raw uploaded dataset (working copies used throughout pipeline).

3. **Automated Dataset Profiling**:
   - Comprehensive taxonomy: Numerical, Categorical, Datetime, Boolean, Identifier columns.
   - Per-column statistics: missing counts & %, unique values, sample records, min, max, mean, median, std.

4. **Robust Data Cleaning Engine**:
   - **Missing Values**: Smart imputation (median for numeric, mode/placeholder for categorical, preserves datetimes).
   - **Duplicate Removal**: Identifies and drops exact duplicate rows with detailed before/after counts.
   - **Datatype Conversion**: Safe parsing of numeric strings and datetime formats.
   - **Text Standardization**: Trims whitespace and normalizes NA indicators across text columns.
   - **Outlier Flagging**: Identifies statistical outliers using IQR & Z-score without silent deletion.

5. **Statistical Analysis & Anomaly Detection**:
   - Full numerical summary (quartiles, min, max, std, sum).
   - Categorical frequency & percentage distribution.
   - Category x Metric group aggregations.
   - Pearson correlation matrices.
   - Multi-dimensional anomaly detection via **Scikit-learn Isolation Forest**.

6. **Interactive Visualizations**:
   - Automatic chart selector (Line for time series, Bar for categories, Scatter for relationships, Histogram & Box for distributions, Heatmap for correlations).
   - Interactive Custom Chart Builder with parameter validation and error messages.

7. **Multi-Format Export Center**:
   - Cleaned CSV download.
   - Cleaned XLSX workbook download.
   - Standalone HTML Audit Report.
   - Executive PDF Audit Report (built via ReportLab).

---

## 📂 Repository Structure

```
KH142-WEB4X/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── src/
│   └── project-source-code/
│       ├── app.py                      # Streamlit UI Application Entry Point
│       ├── config/
│       │   └── settings.py             # Global domain & threshold configurations
│       ├── ingestion/
│       │   └── loader.py               # File loading, encoding & sheet discovery
│       ├── profiling/
│       │   └── profiler.py             # Dataset taxonomy & profiling engine
│       ├── cleaning/
│       │   └── cleaner.py              # Data cleaning & outlier flagging engine
│       ├── analysis/
│       │   ├── statistics.py           # Statistical metrics & trend analyzer
│       │   └── anomalies.py            # IQR, Z-Score & Isolation Forest detector
│       ├── visualization/
│       │   ├── automatic.py            # Automatic Plotly chart generator
│       │   └── user_selected.py        # Custom chart builder & validator
│       ├── reports/
│       │   └── report_generator.py     # Non-AI executive summary & PDF/HTML reports
│       ├── models/
│       │   └── result_models.py        # Structured data classes for pipeline results
│       └── tests/
│           └── test_pipeline.py        # End-to-end Pytest suite
│
├── data/                               # Sample/demo datasets for all 4 domains
│   ├── README.md
│   ├── sales_sample.csv
│   ├── healthcare_sample.csv
│   ├── hr_sample.csv
│   └── finance_sample.xlsx
│
├── docs/                               # System architecture documentation
│   └── README.md
│
└── screenshots/                        # Application preview screenshots
    └── README.md
```

---

## 🛠️ Quick Start & Running Locally

### 1. Environment Setup

Clone the repository and set up a Python virtual environment (Python 3.10+ recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Application

Launch the Streamlit web application:

```bash
streamlit run src/project-source-code/app.py
```

Open your browser at `http://localhost:8501`.

### 3. Run Automated Tests

To execute the test suite across all pipeline components:

```bash
PYTHONPATH=src/project-source-code pytest -v src/project-source-code/tests
```

---

## 📄 License

MIT License
