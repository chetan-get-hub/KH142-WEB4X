import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset_runs = relationship("DatasetRun", back_populates="user", cascade="all, delete-orphan")

class DatasetRun(Base):
    __tablename__ = "dataset_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    sheet_name = Column(String(100), nullable=True)
    domain = Column(String(100), nullable=False, index=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    data_quality_score = Column(Float, default=100.0)
    status = Column(String(50), default="COMPLETED")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="dataset_runs")
    findings = relationship("FindingRecord", back_populates="run", cascade="all, delete-orphan")
    summaries = relationship("SummaryRecord", back_populates="run", cascade="all, delete-orphan")
    reports = relationship("ReportRecord", back_populates="run", cascade="all, delete-orphan")

class FindingRecord(Base):
    __tablename__ = "findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("dataset_runs.id"), nullable=False, index=True)
    finding_id = Column(String(50), nullable=False)
    finding_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False, default="Info", index=True)
    confidence = Column(Float, default=1.0)
    category = Column(String(50), default="General")
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    source_columns = Column(JSON, nullable=True)
    supporting_values = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DatasetRun", back_populates="findings")

class SummaryRecord(Base):
    __tablename__ = "summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("dataset_runs.id"), nullable=False, index=True)
    summary_type = Column(String(50), nullable=False, default="DETERMINISTIC")  # 'AI_GEMINI' or 'DETERMINISTIC'
    content = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DatasetRun", back_populates="summaries")

class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("dataset_runs.id"), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # 'HTML', 'PDF', 'CSV', 'XLSX'
    file_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DatasetRun", back_populates="reports")
