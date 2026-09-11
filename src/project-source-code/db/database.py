"""
DC4X: Data Cleaning For You - Database Engine, Session Maker & Diagnostics
"""
import logging
from urllib.parse import urlparse
from typing import Generator, Tuple, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

Base = declarative_base()

# Connection engine
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10,
    "connect_args": {"connect_timeout": 5}
}

try:
    engine = create_engine(DATABASE_URL, **engine_kwargs)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to create SQLAlchemy engine for {DATABASE_URL}: {e}")
    engine = None
    SessionLocal = None

def get_db() -> Generator:
    """FastAPI database session dependency."""
    if SessionLocal is None:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection() -> Tuple[bool, str]:
    """
    Checks if PostgreSQL connection is operational and returns (is_connected, message).
    """
    if engine is None:
        return False, "Database engine not initialized (check DATABASE_URL)."
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;"))
            result.fetchone()
            return True, "PostgreSQL connected and operational."
    except Exception as e:
        return False, f"Database connection unavailable: {str(e)}"

def get_db_safe_info() -> Dict[str, Any]:
    """
    Returns sanitized database configuration metadata without passwords or secrets.
    """
    is_conn, msg = check_db_connection()
    try:
        parsed = urlparse(DATABASE_URL)
        return {
            "is_connected": is_conn,
            "engine": "PostgreSQL (SQLAlchemy + Psycopg 3)",
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": (parsed.path or "").lstrip("/") or "datacleaning4u",
            "username": parsed.username or "postgres",
            "message": msg,
            "connection_locked": is_conn
        }
    except Exception:
        return {
            "is_connected": is_conn,
            "engine": "PostgreSQL",
            "host": "localhost",
            "port": 5432,
            "database": "datacleaning4u",
            "username": "postgres",
            "message": msg,
            "connection_locked": is_conn
        }

def init_db() -> bool:
    """
    Initializes PostgreSQL tables according to declared SQLAlchemy models.
    """
    if engine is None:
        return False
    try:
        from db import models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("DC4X database tables initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        return False
