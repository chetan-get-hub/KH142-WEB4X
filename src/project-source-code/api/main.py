"""
DC4X: Data Cleaning For You - FastAPI Application & Health Monitoring
"""
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import APP_ENV, GEMINI_MODEL, GEMINI_API_KEY, APP_BRAND, APP_DISPLAY_NAME
from db.database import init_db, get_db_safe_info
from api.schemas.payloads import HealthResponse, DatabaseStatusInfo
from api.routes.analysis import router as analysis_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize PostgreSQL tables for DC4X
    init_db()
    yield

app = FastAPI(
    title="DC4X API",
    description="Backend API service for DC4X (Data Cleaning For You).",
    version="2.1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint reporting API operational status, PostgreSQL connectivity,
    and Google Gemini Free-Tier configuration.
    """
    db_info_dict = get_db_safe_info()
    db_status = DatabaseStatusInfo(**db_info_dict)
    
    clean_key = GEMINI_API_KEY.strip("\"' ")
    gemini_configured = bool(clean_key and len(clean_key) > 5)

    return HealthResponse(
        status="ok",
        app_brand=APP_BRAND,
        app_display_name=APP_DISPLAY_NAME,
        database=db_status,
        gemini_configured=gemini_configured,
        gemini_connected=gemini_configured,
        gemini_model=GEMINI_MODEL,
        app_env=APP_ENV
    )

app.include_router(analysis_router)

if __name__ == "__main__":
    import uvicorn
    from config.settings import BACKEND_HOST, BACKEND_PORT
    uvicorn.run("api.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
