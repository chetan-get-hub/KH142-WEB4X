"""
DataCleaning4U - Configuration Settings
"""

SUPPORTED_DOMAINS = [
    "Sales & Retail",
    "Finance & Banking",
    "Healthcare",
    "Human Resources (HR)"
]

DOMAIN_TAGLINES = {
    "Sales & Retail": "Analyze revenue, order trends, product performance, and customer metrics.",
    "Finance & Banking": "Examine account balances, transaction patterns, risk indicators, and cash flows.",
    "Healthcare": "Evaluate patient metrics, clinical readings, hospital stays, and treatment costs.",
    "Human Resources (HR)": "Assess employee compensation, performance reviews, tenure, and attrition risk."
}

NA_VALUES = [
    "NA", "N/A", "na", "n/a", "NULL", "null", "None", "none",
    "NaN", "nan", "-", "--", "?", "missing", "Missing", " ", ""
]

OUTLIER_IQR_FACTOR = 1.5
OUTLIER_ZSCORE_THRESHOLD = 3.0
