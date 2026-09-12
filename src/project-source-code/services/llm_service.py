"""
DC4X: Data Cleaning For You - Official Google Gemini Free-Tier Service
Converts machine-readable structured findings into natural-language explanations.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from config.settings import GEMINI_API_KEY, GEMINI_MODEL, LLM_FREE_ONLY

logger = logging.getLogger(__name__)

class TableSummaryItem(BaseModel):
    table: str
    summary: str

class AnomalyExplanationItem(BaseModel):
    finding: str
    explanation: str

class AISummaryResponse(BaseModel):
    overall_summary: str = Field(description="Executive narrative summarizing the dataset and business insights.")
    key_findings: List[str] = Field(description="Top key takeaways derived directly from calculated evidence.")
    table_summaries: List[TableSummaryItem] = Field(description="Table or sheet level diagnostic summary.")
    anomalies: List[AnomalyExplanationItem] = Field(description="Explanations of notable outliers and risk observations.")
    data_quality_notes: List[str] = Field(description="Observations on data hygiene, missingness, or formatting.")

class GeminiService:
    """
    Official Google Gemini Free-Tier Service for DC4X.
    Translates verified statistical findings into structured executive narratives.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        if api_key is not None:
            raw_key = api_key
        else:
            raw_key = os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        self.api_key = raw_key.strip("\"' ") if raw_key else ""
        self.model = (model or os.getenv("GEMINI_MODEL", "") or GEMINI_MODEL or "gemini-3.6-flash").strip("\"' ")
        self.free_only = LLM_FREE_ONLY
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google.genai Client: {e}")
                self.client = None

    def is_available(self) -> bool:
        """Returns True if Gemini API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def test_connection(self) -> Tuple[bool, str]:
        """
        Sends a minimal, zero-cost token verification request to confirm live connectivity.
        """
        if not self.is_available():
            return False, "Gemini API key is not configured in .env."
        try:
            if self.client is None:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            
            models_to_try = [self.model, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
            # Deduplicate while preserving order
            unique_models = list(dict.fromkeys(models_to_try))
            
            last_err = ""
            for m in unique_models:
                try:
                    res = self.client.models.generate_content(
                        model=m,
                        contents="Respond with the single word OK."
                    )
                    if res and res.text:
                        return True, f"Google Gemini Free-Tier ({m}) connected successfully."
                except Exception as ex:
                    last_err = str(ex)
                    continue
            return False, f"Gemini connection failed: {last_err}"
        except Exception as e:
            return False, f"Gemini connection failed: {str(e)}"

    def generate_narrative_explanation(
        self,
        pipeline_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes structured pipeline JSON and requests a structured executive explanation
        from Google Gemini Free-Tier API adhering strictly to calculated evidence.
        Includes automatic multi-model failover for 429 rate limit resilience.
        """
        # 1. Check API Key availability
        if not self.is_available():
            return {
                "status": "UNCONFIGURED",
                "message": "Gemini API key is not configured. (Add GEMINI_API_KEY to .env).",
                "ai_summary": None,
                "fallback_used": True,
                "model_used": None
            }

        if self.client is None:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                return {
                    "status": "CLIENT_ERROR",
                    "message": f"Could not initialize Gemini client: {str(e)}",
                    "ai_summary": None,
                    "fallback_used": True,
                    "model_used": None
                }

        # 2. Build strict, evidence-first system & user prompt
        domain = pipeline_payload.get("domain", "General")
        file_name = pipeline_payload.get("file_name", "dataset")
        overview = pipeline_payload.get("dataset_overview", {})
        cleaning = pipeline_payload.get("cleaning_metrics", {})
        findings = pipeline_payload.get("structured_findings", [])
        anomalies = pipeline_payload.get("anomaly_summary", {})
        stats = pipeline_payload.get("statistical_summary", {})

        system_instruction = (
            "You are the executive AI data explanation engine for DC4X (Data Cleaning For You). "
            "Your objective is to provide a clear narrative explanation of verified statistical calculations. "
            f"The target business domain is '{domain}'.\n\n"
            "STRICT OPERATIONAL RULES:\n"
            "1. You MUST ONLY explain the verified facts and statistics provided in the payload.\n"
            "2. NEVER invent, extrapolate, or hallucinate numbers not present in the data.\n"
            "3. NEVER claim correlation proves causation.\n"
            "4. Clearly distinguish calculated facts from strategic business interpretations.\n"
            "5. Translate technical statistics into plain, actionable language for decision makers.\n"
            "6. Keep language crisp, professional, and highlight critical anomalies."
        )

        user_content = {
            "target_domain": domain,
            "dataset_name": file_name,
            "overview": overview,
            "cleaning_operations": cleaning,
            "evidence_backed_findings": findings[:12],
            "anomaly_and_risk_audit": anomalies,
            "numerical_summary": stats.get("numerical", {}),
            "group_aggregations": stats.get("group_aggregations", {}),
            "trends": stats.get("trends", {})
        }

        prompt_str = (
            f"Analyze and explain the following verified dataset findings for '{file_name}' in the '{domain}' domain.\n\n"
            f"Data Payload:\n{json.dumps(user_content, indent=2)}\n\n"
            "Generate a structured narrative explanation adhering strictly to the output schema."
        )

        models_to_try = [self.model, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
        unique_models = list(dict.fromkeys(models_to_try))

        last_err_msg = ""
        for current_model in unique_models:
            try:
                from google.genai import types

                response = self.client.models.generate_content(
                    model=current_model,
                    contents=prompt_str,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=AISummaryResponse,
                        temperature=0.2
                    )
                )

                if response and response.text:
                    parsed_json = json.loads(response.text)
                    return {
                        "status": "SUCCESS",
                        "message": "AI narrative explanation generated successfully.",
                        "ai_summary": parsed_json,
                        "fallback_used": False,
                        "model_used": current_model
                    }
            except Exception as e:
                err_msg = str(e)
                last_err_msg = err_msg
                logger.warning(f"Gemini API request with model {current_model} encountered error: {err_msg}")
                # Try next model in list on rate limit or model unavailable
                continue

        # If all candidate models failed, report status and revert to deterministic summary
        if "429" in last_err_msg or "RESOURCE_EXHAUSTED" in last_err_msg or "quota" in last_err_msg.lower():
            status_label = "RATE_LIMIT_QUOTA_EXCEEDED"
            user_friendly = "Gemini Free-Tier rate limit reached across models. Reverting to deterministic summary."
        else:
            status_label = "API_ERROR"
            user_friendly = f"Gemini API Error ({last_err_msg}). Reverting to deterministic summary."

        return {
            "status": status_label,
            "message": user_friendly,
            "ai_summary": None,
            "fallback_used": True,
            "model_used": self.model
        }
