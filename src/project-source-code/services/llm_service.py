import os
import json
import logging
from typing import Dict, Any, Optional, List
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
    Official Google Gemini Free-Tier Service for DataCleaning4U.
    Converts machine-readable structured findings into natural-language explanations.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "") or GEMINI_API_KEY
        self.model = model or os.getenv("GEMINI_MODEL", "") or GEMINI_MODEL or "gemini-2.5-flash"
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
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def generate_narrative_explanation(
        self,
        pipeline_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes structured pipeline JSON (from to_serializable_dict) and requests
        a structured natural-language explanation from Google Gemini Free-Tier API.
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
            "You are the autonomous data analyst agent for DataCleaning4U. "
            "Your objective is to provide an executive explanation of the supplied statistical analysis results. "
            f"The target domain is '{domain}'.\n\n"
            "STRICT RULES:\n"
            "1. You MUST ONLY explain the verified facts provided in the payload.\n"
            "2. NEVER invent, hallucinate, or estimate numbers not in the data.\n"
            "3. NEVER claim correlation proves causation.\n"
            "4. Clearly distinguish calculated facts from business interpretations.\n"
            "5. Translate statistical formulas into plain, actionable language for executives.\n"
            "6. Keep language concise, professional, and highlight high-severity findings."
        )

        user_content = {
            "target_domain": domain,
            "dataset_name": file_name,
            "overview": overview,
            "cleaning_operations": cleaning,
            "evidence_backed_findings": findings[:10],
            "anomaly_and_risk_audit": anomalies,
            "numerical_summary": stats.get("numerical", {}),
            "group_aggregations": stats.get("group_aggregations", {}),
            "trends": stats.get("trends", {})
        }

        prompt_str = (
            f"Analyze and explain the following verified dataset findings for '{file_name}' in the '{domain}' domain.\n\n"
            f"Data Payload:\n{json.dumps(user_content, indent=2)}\n\n"
            "Generate a structured narrative explanation adhering to the output schema."
        )

        try:
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.model,
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
                    "model_used": self.model
                }
            else:
                return {
                    "status": "EMPTY_RESPONSE",
                    "message": "Gemini API returned an empty response.",
                    "ai_summary": None,
                    "fallback_used": True,
                    "model_used": self.model
                }

        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Gemini API request encountered an error: {err_msg}")
            
            # Handle rate limit (429) specifically
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                status_label = "RATE_LIMIT_QUOTA_EXCEEDED"
                user_friendly = "Gemini Free-Tier rate limit reached. Reverting to deterministic summary."
            else:
                status_label = "API_ERROR"
                user_friendly = f"Gemini API Error ({err_msg}). Reverting to deterministic summary."

            return {
                "status": status_label,
                "message": user_friendly,
                "ai_summary": None,
                "fallback_used": True,
                "model_used": self.model
            }
