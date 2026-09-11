"""
DC4X: Data Cleaning For You - Configuration Settings, Domain Metadata & Environment Loading
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env file in project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_paths = [
    BASE_DIR / ".env",
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent / ".env"
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        break

# Branding Constants
APP_BRAND = "DC4X"
APP_DISPLAY_NAME = "Data Cleaning For You"
APP_TITLE = "DC4X | Data Cleaning For You"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"
LOGO_DARK_PATH = ASSETS_DIR / "logo_dark.png"
LOGO_LIGHT_PATH = ASSETS_DIR / "logo_light.png"
LOGO_SVG_PATH = ASSETS_DIR / "logo.svg"

# 1. Environment & API Settings
APP_ENV = os.getenv("APP_ENV", "development").strip("\"' ")
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1").strip("\"' ")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}").strip("\"' ")

# 2. Google Gemini Free-Tier API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip("\"' ")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip("\"' ")
LLM_FREE_ONLY = os.getenv("LLM_FREE_ONLY", "true").strip("\"' ").lower() in ["true", "1", "yes"]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip("\"' ")

# 3. PostgreSQL Database Connection (SQLAlchemy + Psycopg 3)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/datacleaning4u"
).strip("\"' ")

# Supported Domains & Metadata
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

# Domain keyword dictionaries for conservative semantic inference & prioritization
DOMAIN_KEYWORDS = {
    "Sales & Retail": {
        "metrics": ["sales", "revenue", "profit", "amount", "units", "quantity", "price", "discount", "margin", "cost", "rating", "order", "salesamount", "unitssold", "customerrating"],
        "groups": ["category", "region", "product", "customer", "channel", "store", "segment", "brand", "item", "state", "city", "country"],
        "time": ["date", "orderdate", "month", "quarter", "year", "timestamp", "day", "week"],
        "id": ["transactionid", "orderid", "customerid", "productid", "itemid", "invoiceid", "sku"]
    },
    "Finance & Banking": {
        "metrics": ["amount", "balance", "creditscore", "currentbalance", "income", "expense", "interest", "loan", "debt", "risk", "rate", "fee", "principal", "payment"],
        "groups": ["txtype", "type", "status", "branch", "accounttype", "category", "risklevel", "rating", "segment"],
        "time": ["txdate", "date", "timestamp", "month", "quarter", "year", "duedate", "settledate"],
        "id": ["accountno", "accountnumber", "txid", "transactionid", "customerid", "loanid"]
    },
    "Healthcare": {
        "metrics": ["systolicbp", "diastolicbp", "bloodpressure", "bp", "cholesterol", "treatmentcost", "cost", "age", "bmi", "glucose", "heartrate", "stayduration", "days", "dosage"],
        "groups": ["department", "diagnosis", "doctor", "hospital", "ward", "gender", "discharged", "status", "district", "region", "condition"],
        "time": ["admissiondate", "dischargedate", "date", "visitdate", "timestamp", "year", "month"],
        "id": ["patientid", "recordid", "admissionid", "mrn", "doctorid"]
    },
    "Human Resources (HR)": {
        "metrics": ["salary", "performancescore", "yearsexperience", "experience", "age", "tenure", "bonus", "compensation", "rating", "hours", "overtime", "leaves"],
        "groups": ["department", "attritionrisk", "position", "role", "jobtitle", "level", "location", "gender", "education", "status", "performance"],
        "time": ["joindate", "hiredate", "exitdate", "reviewdate", "date", "year", "month"],
        "id": ["empid", "employeeid", "staffid", "badgeid", "userid"]
    }
}

NA_VALUES = [
    "NA", "N/A", "na", "n/a", "NULL", "null", "None", "none",
    "NaN", "nan", "-", "--", "?", "missing", "Missing", " ", ""
]

OUTLIER_IQR_FACTOR = 1.5
OUTLIER_ZSCORE_THRESHOLD = 3.0
CORRELATION_STRONG_THRESHOLD = 0.70
CORRELATION_MODERATE_THRESHOLD = 0.40
SIGNIFICANT_CHANGE_THRESHOLD_PCT = 15.0
GROUP_DIFFERENCE_THRESHOLD_PCT = 25.0
DOMINANT_CATEGORY_THRESHOLD_PCT = 40.0
