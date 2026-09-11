import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import APP_ENV, GEMINI_MODEL, GEMINI_API_KEY
from db.database import init_db, check_db_connection
from api.schemas.payloads import HealthResponse
from api.routes.analysis import router as analysis_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables
    init_db()
    yield
    # Shutdown logic if any

app = FastAPI(
    title="DataCleaning4U API",
    description="Backend API service for DataCleaning4U autonomous data analysis agent.",
    version="2.0.0",
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
    db_ok, db_msg = check_db_connection()
    gemini_ok = bool(GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 5)

    return HealthResponse(
        status="ok",
        database_connected=db_ok,
        database_message=db_msg,
        gemini_configured=gemini_ok,
        gemini_model=GEMINI_MODEL,
        app_env=APP_ENV
    )

app.include_router(analysis_router)

if __name__ == "__main__":
    import uvicorn
    from config.settings import BACKEND_HOST, BACKEND_PORT
    uvicorn.run("api.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
