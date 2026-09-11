"""
DC4X: Data Cleaning For You - Analysis Run Ingestion & History API Endpoints
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, DatasetRun, FindingRecord, SummaryRecord, generate_run_code
from api.schemas.payloads import (
    AnalysisRunCreate,
    AnalysisRunResponse,
    DetailedAnalysisRunResponse,
    FindingItemResponse
)
from services.llm_service import GeminiService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])

@router.post("/runs", response_model=AnalysisRunResponse, status_code=status.HTTP_201_CREATED)
def create_analysis_run(
    payload: AnalysisRunCreate,
    db: Optional[Session] = Depends(get_db)
):
    """
    Ingests structured pipeline analysis results, persists metadata & findings into PostgreSQL,
    and synthesizes an AI narrative explanation via Google Gemini Free-Tier.
    """
    row_cnt = payload.dataset_overview.get("total_rows", 0)
    col_cnt = payload.dataset_overview.get("total_columns", 0)

    # 1. Trigger Gemini Narrative Synthesis if requested
    ai_status = "NOT_REQUESTED"
    ai_summary_dict = None
    model_name = None

    if payload.trigger_ai_summary:
        gemini_svc = GeminiService()
        ai_res = gemini_svc.generate_narrative_explanation(payload.model_dump())
        ai_status = ai_res.get("status", "FAILED")
        ai_summary_dict = ai_res.get("ai_summary")
        model_name = ai_res.get("model_used")

    # 2. Persist to PostgreSQL if database session is operational
    run_id = None
    run_code = generate_run_code()
    created_at = None

    if db is not None:
        try:
            # Ensure User exists
            uname = payload.username or "analyst@dc4x.io"
            user = db.query(User).filter(User.username == uname).first()
            if not user:
                user = User(username=uname, email=uname)
                db.add(user)
                db.flush()

            # Create DatasetRun record
            run = DatasetRun(
                run_code=run_code,
                user_id=user.id,
                file_name=payload.file_name,
                file_type=payload.file_name.split(".")[-1].upper() if "." in payload.file_name else "CSV",
                sheet_name=payload.sheet_name,
                domain=payload.domain,
                row_count=row_cnt,
                column_count=col_cnt,
                data_quality_score=100.0,
                status="COMPLETED",
                metadata_json={
                    "dataset_overview": payload.dataset_overview,
                    "cleaning_metrics": payload.cleaning_metrics,
                    "statistical_summary": payload.statistical_summary,
                    "anomaly_summary": payload.anomaly_summary
                }
            )
            db.add(run)
            db.flush()
            run_id = run.id
            run_code = run.run_code
            created_at = run.created_at

            # Persist Findings
            for f in payload.structured_findings:
                f_rec = FindingRecord(
                    run_id=run.id,
                    finding_id=f.get("id") or f.get("finding_id") or "FND_000",
                    finding_type=f.get("type") or f.get("finding_type") or "GENERAL",
                    title=f.get("title", ""),
                    severity=f.get("severity", "Info"),
                    confidence=float(f.get("confidence", 1.0)),
                    category=f.get("category", "General"),
                    description=f.get("description", ""),
                    evidence=str(f.get("evidence", "")),
                    source_columns=f.get("source_columns", []),
                    supporting_values=f.get("supporting_values", {})
                )
                db.add(f_rec)

            # Persist Deterministic Summary
            det_sum = SummaryRecord(
                run_id=run.id,
                summary_type="DETERMINISTIC",
                content=payload.executive_summary_text,
                model_name="DC4X-Engine"
            )
            db.add(det_sum)

            # Persist AI Summary if generated
            if ai_summary_dict:
                ai_sum_rec = SummaryRecord(
                    run_id=run.id,
                    summary_type="AI_GEMINI",
                    content=json.dumps(ai_summary_dict),
                    model_name=model_name or "gemini-3.6-flash"
                )
                db.add(ai_sum_rec)

            db.commit()
            db.refresh(run)

        except Exception as db_err:
            db.rollback()
            logger.error(f"Database persistence error: {db_err}")
            run_id = f"fallback-{payload.file_name}"
    else:
        run_id = f"in-memory-{payload.file_name}"

    return AnalysisRunResponse(
        run_id=run_id or f"run-{payload.file_name}",
        run_code=run_code,
        file_name=payload.file_name,
        domain=payload.domain,
        sheet_name=payload.sheet_name,
        row_count=row_cnt,
        column_count=col_cnt,
        data_quality_score=100.0,
        status="COMPLETED",
        findings_count=len(payload.structured_findings),
        ai_status=ai_status,
        ai_summary=ai_summary_dict,
        deterministic_summary=payload.executive_summary_text,
        created_at=created_at
    )

@router.get("/runs", response_model=List[AnalysisRunResponse])
def list_analysis_runs(
    limit: int = 50,
    db: Optional[Session] = Depends(get_db)
):
    """Lists recent analysis runs stored in PostgreSQL, sorted newest first."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database session unavailable.")

    runs = db.query(DatasetRun).order_by(DatasetRun.created_at.desc()).limit(limit).all()
    results = []
    for r in runs:
        det_sum = next((s.content for s in r.summaries if s.summary_type == "DETERMINISTIC"), "")
        ai_sum_rec = next((s for s in r.summaries if s.summary_type == "AI_GEMINI"), None)
        
        parsed_ai = None
        if ai_sum_rec and ai_sum_rec.content:
            try:
                parsed_ai = json.loads(ai_sum_rec.content)
            except Exception:
                parsed_ai = None

        results.append(AnalysisRunResponse(
            run_id=r.id,
            run_code=r.run_code or f"DC4X-{r.id[:6].upper()}",
            file_name=r.file_name,
            domain=r.domain,
            sheet_name=r.sheet_name,
            row_count=r.row_count,
            column_count=r.column_count,
            data_quality_score=r.data_quality_score or 100.0,
            status=r.status,
            findings_count=len(r.findings),
            ai_status="SUCCESS" if ai_sum_rec else "NONE",
            ai_summary=parsed_ai,
            deterministic_summary=det_sum,
            created_at=r.created_at
        ))
    return results

@router.get("/runs/{run_identifier}", response_model=DetailedAnalysisRunResponse)
def get_analysis_run(
    run_identifier: str,
    db: Optional[Session] = Depends(get_db)
):
    """Retrieves a specific analysis run with its complete findings and metadata by ID or run_code."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database session unavailable.")

    r = db.query(DatasetRun).filter(
        (DatasetRun.id == run_identifier) | (DatasetRun.run_code == run_identifier)
    ).first()

    if not r:
        raise HTTPException(status_code=404, detail=f"Analysis run '{run_identifier}' not found.")

    det_sum = next((s.content for s in r.summaries if s.summary_type == "DETERMINISTIC"), "")
    ai_sum_rec = next((s for s in r.summaries if s.summary_type == "AI_GEMINI"), None)

    parsed_ai = None
    if ai_sum_rec and ai_sum_rec.content:
        try:
            parsed_ai = json.loads(ai_sum_rec.content)
        except Exception:
            parsed_ai = None

    finding_items = [
        FindingItemResponse(
            finding_id=f.finding_id,
            finding_type=f.finding_type,
            title=f.title,
            severity=f.severity,
            confidence=f.confidence,
            category=f.category,
            description=f.description,
            evidence=f.evidence,
            source_columns=f.source_columns if isinstance(f.source_columns, list) else []
        )
        for f in r.findings
    ]

    return DetailedAnalysisRunResponse(
        run_id=r.id,
        run_code=r.run_code or f"DC4X-{r.id[:6].upper()}",
        file_name=r.file_name,
        domain=r.domain,
        sheet_name=r.sheet_name,
        row_count=r.row_count,
        column_count=r.column_count,
        data_quality_score=r.data_quality_score or 100.0,
        status=r.status,
        findings_count=len(r.findings),
        ai_status="SUCCESS" if ai_sum_rec else "NONE",
        ai_summary=parsed_ai,
        deterministic_summary=det_sum,
        created_at=r.created_at,
        metadata_json=r.metadata_json or {},
        findings=finding_items
    )
