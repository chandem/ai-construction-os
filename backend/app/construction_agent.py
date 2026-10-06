"""Gemini-powered construction tool-calling agent."""
from __future__ import annotations

import json

from google import genai
from google.genai import types
from supabase import Client

from .config import settings
from .cost_intelligence import make_project_cost_intelligence_tool
from .procurement_intelligence import make_project_procurement_intelligence_tool
from .schedule_intelligence import make_project_schedule_intelligence_tool
from .construction_tools import (
    calculate_concrete_volume,
    calculate_material_balance,
    calculate_project_progress,
)
from .project_data import (
    make_document_search_tool,
    make_project_action_plan_tool,
    make_project_monitoring_tool,
    make_project_risk_analysis_tool,
    make_project_forecast_tool,
    make_project_early_warnings_tool,
    make_project_management_recommendations_tool,
    make_project_performance_score_tool,
    make_project_priorities_tool,
    make_project_summary_tool,
)

CONSTRUCTION_AGENT_SYSTEM = """You are the Construction AI Agent inside an AI-first Construction OS.

The user message includes UPLOADED DOCUMENT CONTEXT. Use that context first for questions about
uploaded files, drawings, specifications, contracts, reports, bills of quantities, or maintenance plans.
Quote the excerpts and cite the document name. If the context has files but no excerpts, say the files
are uploaded and repeat the note. Do not call this a system error unless the note says the lookup failed.

Use get_project_summary for current project status, activities, materials, equipment, costs, or risks.
Use get_project_priorities when the user asks what to focus on, what needs attention, recommended
next actions, or project priorities.
Use get_project_action_plan when the user asks for an ordered action plan, implementation steps,
owners, or what to do next. The action plan is advisory and must not modify project records.
Use get_project_monitoring when the user asks how the project is performing, what needs attention,
what is critical, what is on track, schedule variance, or what management should decide next.
Monitoring is read-only and must be based only on currently recorded project data.
Use get_project_risk_analysis when the user asks about recorded project risks, risk priorities,
mitigation, or risk-control gaps.
Use get_project_forecast when the user asks what is likely to happen, project forecasting,
forecast readiness, or future performance.
Use get_project_early_warnings when the user asks for early warnings, emerging issues,
preventive alerts, or what could become a problem if current conditions persist.
Use get_project_management_recommendations when the user asks what management should do,
what decisions should be prioritized, or asks for a consolidated management recommendation.
Use get_project_performance_score when the user asks for a project performance score, project health score,
overall project score, or a transparent assessment of project performance.
Use get_project_cost_intelligence when the user asks about project costs, cost intelligence, budget versus actual,
cost overruns, cost concentration, cost controls, or cost-data gaps. Never infer an overrun without an approved baseline.
Use get_project_procurement_intelligence when the user asks about procurement, purchasing, material ordering,
delivery status, procurement priorities, supplier delays, outstanding quantities, or procurement risks.
Do not invent procurement quantities, supplier status, dates, or shortages.
Use get_project_schedule_intelligence when the user asks about schedule performance, activities behind plan,
planned versus actual progress, schedule variance, or schedule priorities. Do not infer calendar delays,
completion dates, or future outcomes when those fields are not recorded.
Forecasting must distinguish
recorded facts from conditional scenarios and must not invent future values.
Use calculation tools for concrete volume, project progress percentage, and remaining material quantity.
You may also call search_uploaded_documents if the preloaded context is not enough.

Do not invent project-specific facts, quantities, dates, costs, or document contents.
If the available data is insufficient, say what is missing.
For engineering, safety, contractual, or financial decisions, calculations and excerpts do not
replace review by a qualified professional or the governing project documents.
"""

BASE_CONSTRUCTION_TOOLS = [
    calculate_concrete_volume,
    calculate_project_progress,
    calculate_material_balance,
]

_TRANSIENT_ERROR_MARKERS = (
    "429",
    "resource_exhausted",
    "rate_limit",
    "rate limit",
    "too_many_requests",
    "503",
    "service_unavailable",
    "temporarily unavailable",
    "temporarily overloaded",
    "overloaded",
    "unavailable",
    "deadline exceeded",
    "timeout",
)


def _is_transient_gemini_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_ERROR_MARKERS)


def _document_context(document_search_tool, message: str) -> str:
    try:
        found = document_search_tool(message)
    except Exception as exc:
        found = {"matches": [], "note": "Document lookup failed: %s" % exc}
    return json.dumps(found, default=str)[:8000]


def _generate_with_model(
    client: genai.Client,
    model_id: str,
    message: str,
    project_id: str,
    project_summary_tool,
    project_priorities_tool,
    project_action_plan_tool,
    project_monitoring_tool,
    project_risk_analysis_tool,
    project_forecast_tool,
    project_early_warnings_tool,
    project_management_recommendations_tool,
    project_performance_score_tool,
    project_cost_intelligence_tool,
    project_procurement_intelligence_tool,
    project_schedule_intelligence_tool,
    document_search_tool,
):
    context = _document_context(document_search_tool, message)
    chat = client.chats.create(
        model=model_id,
        config=types.GenerateContentConfig(
            system_instruction=CONSTRUCTION_AGENT_SYSTEM,
            temperature=0.2,
            tools=[
                *BASE_CONSTRUCTION_TOOLS,
                project_summary_tool,
                project_priorities_tool,
                project_action_plan_tool,
                project_monitoring_tool,
                project_risk_analysis_tool,
                project_forecast_tool,
                project_early_warnings_tool,
                project_management_recommendations_tool,
                project_performance_score_tool,
                project_cost_intelligence_tool,
                project_procurement_intelligence_tool,
                project_schedule_intelligence_tool,
                document_search_tool,
            ],
        ),
    )
    return chat.send_message(
        "AUTHORIZED PROJECT ID: %s\n\nUPLOADED DOCUMENT CONTEXT:\n%s\n\nUSER REQUEST:\n%s"
        % (project_id, context, message)
    )


def run_construction_agent(
    message: str,
    project_id: str,
    db: Client,
    model: str | None = None,
) -> str:
    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.ai_api_key)
    model_id = model or settings.resolved_chat_model
    models_to_try = [model_id, *settings.resolved_chat_fallback_models]
    project_summary_tool = make_project_summary_tool(db, project_id)
    project_priorities_tool = make_project_priorities_tool(db, project_id)
    project_action_plan_tool = make_project_action_plan_tool(db, project_id)
    project_monitoring_tool = make_project_monitoring_tool(db, project_id)
    project_risk_analysis_tool = make_project_risk_analysis_tool(db, project_id)
    project_forecast_tool = make_project_forecast_tool(db, project_id)
    project_early_warnings_tool = make_project_early_warnings_tool(db, project_id)
    project_management_recommendations_tool = make_project_management_recommendations_tool(db, project_id)
    project_performance_score_tool = make_project_performance_score_tool(db, project_id)
    project_cost_intelligence_tool = make_project_cost_intelligence_tool(db, project_id)
    project_procurement_intelligence_tool = make_project_procurement_intelligence_tool(db, project_id)
    project_schedule_intelligence_tool = make_project_schedule_intelligence_tool(db, project_id)
    document_search_tool = make_document_search_tool(db, project_id)

    last_error: Exception | None = None

    for index, candidate_model in enumerate(models_to_try):
        try:
            response = _generate_with_model(
                client,
                candidate_model,
                message,
                project_id,
                project_summary_tool,
                project_priorities_tool,
                project_action_plan_tool,
                project_monitoring_tool,
                project_risk_analysis_tool,
                project_forecast_tool,
                project_early_warnings_tool,
                project_management_recommendations_tool,
                project_performance_score_tool,
                project_cost_intelligence_tool,
                project_procurement_intelligence_tool,
                project_schedule_intelligence_tool,
                document_search_tool,
            )
            return (response.text or "").strip()
        except Exception as exc:
            last_error = exc
            is_last_model = index == len(models_to_try) - 1
            if is_last_model or not _is_transient_gemini_error(exc):
                raise

    if last_error is not None:
        raise last_error

    raise RuntimeError("No Gemini chat model is configured")
