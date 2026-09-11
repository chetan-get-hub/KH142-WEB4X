"""
DC4X: Data Cleaning For You - Backend API Client with In-Process Database Fallback
"""
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from config.settings import BACKEND_URL, GEMINI_API_KEY, GEMINI_MODEL, APP_ENV, APP_BRAND, APP_DISPLAY_NAME
from db.database import get_db_safe_info, SessionLocal
from db.models import User, DatasetRun, FindingRecord, SummaryRecord, generate_run_code
from services.llm_service import GeminiService

logger = logging.getLogger(__name__)

class BackendClient:
    """
    Client interface for connecting Streamlit frontend to FastAPI backend and PostgreSQL persistence.
    If the FastAPI HTTP server is offline or unreachable, seamlessly falls back to direct in-process
    PostgreSQL persistence and Gemini service calls without interrupting the user.
    """

    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> Dict[str, Any]:
        """Checks FastAPI health or directly evaluates DB & Gemini status."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                data["backend_online"] = True
                return data
        except Exception:
            pass

        # Fallback to in-process diagnostics
        db_info = get_db_safe_info()
        clean_key = GEMINI_API_KEY.strip("\"' ")
        gemini_configured = bool(clean_key and len(clean_key) > 5)

        return {
            "status": "ok",
            "app_brand": APP_BRAND,
            "app_display_name": APP_DISPLAY_NAME,
            "backend_online": False,
            "database": db_info,
            "gemini_configured": gemini_configured,
            "gemini_connected": gemini_configured,
            "gemini_model": GEMINI_MODEL,
            "app_env": APP_ENV
        }

    def submit_analysis_run(
        self,
        serializable_pipeline_dict: Dict[str, Any],
        trigger_ai_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Sends structured pipeline payload to FastAPI backend.
        Falls back to in-process persistence and Gemini execution if API endpoint is unavailable.
        """
        payload = {
            "domain": serializable_pipeline_dict.get("domain", "General"),
            "file_name": serializable_pipeline_dict.get("file_name", "dataset"),
            "sheet_name": serializable_pipeline_dict.get("sheet_name"),
            "username": "analyst@dc4x.io",
            "trigger_ai_summary": trigger_ai_summary,
            "dataset_overview": serializable_pipeline_dict.get("dataset_overview", {}),
            "cleaning_metrics": serializable_pipeline_dict.get("cleaning_metrics", {}),
            "statistical_summary": serializable_pipeline_dict.get("statistical_summary", {}),
            "anomaly_summary": serializable_pipeline_dict.get("anomaly_summary", {}),
            "structured_findings": serializable_pipeline_dict.get("structured_findings", []),
            "executive_summary_text": serializable_pipeline_dict.get("executive_summary_text", "")
        }

        # 1. Try FastAPI endpoint
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/analysis/runs",
                json=payload,
                timeout=35.0
            )
            if resp.status_code == 201:
                return resp.json()
        except Exception as e:
            logger.warning(f"FastAPI backend unreachable ({e}). Using in-process engine.")

        # 2. In-process direct fallback
        return self._in_process_analysis_run(payload, trigger_ai_summary)

    def list_historical_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves list of past analysis runs from FastAPI or directly from PostgreSQL."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/analysis/runs?limit={limit}", timeout=3.5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        # In-process PostgreSQL fallback
        if SessionLocal is None:
            return []

        db = SessionLocal()
        try:
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

                results.append({
                    "run_id": r.id,
                    "run_code": r.run_code or f"DC4X-{r.id[:6].upper()}",
                    "file_name": r.file_name,
                    "domain": r.domain,
                    "sheet_name": r.sheet_name,
                    "row_count": r.row_count,
                    "column_count": r.column_count,
                    "data_quality_score": r.data_quality_score or 100.0,
                    "status": r.status,
                    "findings_count": len(r.findings),
                    "ai_status": "SUCCESS" if ai_sum_rec else "NONE",
                    "ai_summary": parsed_ai,
                    "deterministic_summary": det_sum,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })
            return results
        except Exception as e:
            logger.error(f"Error querying historical runs: {e}")
            return []
        finally:
            db.close()

    def get_historical_run(self, run_identifier: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete details of a past analysis run."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/analysis/runs/{run_identifier}", timeout=4.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        # In-process PostgreSQL fallback
        if SessionLocal is None:
            return None

        db = SessionLocal()
        try:
            r = db.query(DatasetRun).filter(
                (DatasetRun.id == run_identifier) | (DatasetRun.run_code == run_identifier)
            ).first()

            if not r:
                return None

            det_sum = next((s.content for s in r.summaries if s.summary_type == "DETERMINISTIC"), "")
            ai_sum_rec = next((s for s in r.summaries if s.summary_type == "AI_GEMINI"), None)

            parsed_ai = None
            if ai_sum_rec and ai_sum_rec.content:
                try:
                    parsed_ai = json.loads(ai_sum_rec.content)
                except Exception:
                    parsed_ai = None

            findings_list = [
                {
                    "finding_id": f.finding_id,
                    "finding_type": f.finding_type,
                    "title": f.title,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "category": f.category,
                    "description": f.description,
                    "evidence": f.evidence,
                    "source_columns": f.source_columns or []
                }
                for f in r.findings
            ]

            return {
                "run_id": r.id,
                "run_code": r.run_code or f"DC4X-{r.id[:6].upper()}",
                "file_name": r.file_name,
                "domain": r.domain,
                "sheet_name": r.sheet_name,
                "row_count": r.row_count,
                "column_count": r.column_count,
                "data_quality_score": r.data_quality_score or 100.0,
                "status": r.status,
                "findings_count": len(r.findings),
                "ai_status": "SUCCESS" if ai_sum_rec else "NONE",
                "ai_summary": parsed_ai,
                "deterministic_summary": det_sum,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "metadata_json": r.metadata_json or {},
                "findings": findings_list
            }
        except Exception as e:
            logger.error(f"Error fetching historical run {run_identifier}: {e}")
            return None
        finally:
            db.close()

    def _in_process_analysis_run(self, payload: Dict[str, Any], trigger_ai: bool) -> Dict[str, Any]:
        """Executes in-process Gemini narrative and PostgreSQL insertion."""
        ai_status = "NOT_REQUESTED"
        ai_summary_dict = None
        model_used = None

        if trigger_ai:
            svc = GeminiService()
            ai_res = svc.generate_narrative_explanation(payload)
            ai_status = ai_res.get("status", "FAILED")
            ai_summary_dict = ai_res.get("ai_summary")
            model_used = ai_res.get("model_used")

        run_id = None
        run_code = generate_run_code()

        if SessionLocal is not None:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == "analyst@dc4x.io").first()
                if not user:
                    user = User(username="analyst@dc4x.io", email="analyst@dc4x.io")
                    db.add(user)
                    db.flush()

                run = DatasetRun(
                    run_code=run_code,
                    user_id=user.id,
                    file_name=payload.get("file_name", "dataset"),
                    file_type="CSV",
                    sheet_name=payload.get("sheet_name"),
                    domain=payload.get("domain", "General"),
                    row_count=payload.get("dataset_overview", {}).get("total_rows", 0),
                    column_count=payload.get("dataset_overview", {}).get("total_columns", 0),
                    status="COMPLETED",
                    metadata_json={
                        "dataset_overview": payload.get("dataset_overview"),
                        "cleaning_metrics": payload.get("cleaning_metrics"),
                        "statistical_summary": payload.get("statistical_summary"),
                        "anomaly_summary": payload.get("anomaly_summary")
                    }
                )
                db.add(run)
                db.flush()
                run_id = run.id
                run_code = run.run_code

                for f in payload.get("structured_findings", []):
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
                        source_columns=f.get("source_columns", [])
                    )
                    db.add(f_rec)

                det_sum = SummaryRecord(
                    run_id=run.id,
                    summary_type="DETERMINISTIC",
                    content=payload.get("executive_summary_text", ""),
                    model_name="DC4X-Engine"
                )
                db.add(det_sum)

                if ai_summary_dict:
                    ai_rec = SummaryRecord(
                        run_id=run.id,
                        summary_type="AI_GEMINI",
                        content=json.dumps(ai_summary_dict),
                        model_name=model_used or "gemini-3.6-flash"
                    )
                    db.add(ai_rec)

                db.commit()
            except Exception as ex:
                db.rollback()
                logger.error(f"In-process DB write error: {ex}")
                run_id = f"fallback-{payload.get('file_name')}"
            finally:
                db.close()

        return {
            "run_id": run_id or f"in-mem-{payload.get('file_name')}",
            "run_code": run_code,
            "file_name": payload.get("file_name"),
            "domain": payload.get("domain"),
            "sheet_name": payload.get("sheet_name"),
            "row_count": payload.get("dataset_overview", {}).get("total_rows", 0),
            "column_count": payload.get("dataset_overview", {}).get("total_columns", 0),
            "status": "COMPLETED",
            "findings_count": len(payload.get("structured_findings", [])),
            "ai_status": ai_status,
            "ai_summary": ai_summary_dict,
            "deterministic_summary": payload.get("executive_summary_text", "")
        }
