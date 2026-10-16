"""Gemini-powered construction tool-calling agent."""
from __future__ import annotations

import json
from typing import Any, Callable

from google import genai
from google.genai import types
from supabase import Client

from .config import settings
from .cost_intelligence import make_project_cost_intelligence_tool
from .procurement_intelligence import make_project_procurement_intelligence_tool
from .schedule_intelligence import make_project_schedule_intelligence_tool
from .risk_prediction import make_project_risk_prediction_tool
from .contract_intelligence import make_project_contract_intelligence_tool
from .boq_intelligence import make_project_boq_intelligence_tool
from .document_intelligence_tool import make_project_document_intelligence_tool
from .executive_dashboard import make_project_executive_dashboard_tool
from .resource_optimization import make_project_resource_optimization_tool
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

Only a focused subset of tools is available for each request. Prefer the most specific matching tool.
Use get_project_summary for current project status when no narrower tool applies.
Use search_uploaded_documents when you need more document text than the preloaded context.
Use calculation tools for concrete volume, project progress percentage, and remaining material quantity.

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

# Keyword groups for selective tool loading (free-tier Gemini handles fewer tools more reliably).
_TOOL_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "document": (
        "document",
        "upload",
        "file",
        "pdf",
        "drawing",
        "spec",
        "processed",
        "reprocess",
        "extract",
        "searchable",
        "chunk",
        "ocr",
    ),
    "boq": ("boq", "bill of quant", "quantity", "quantities", "unit rate", "work section"),
    "cost": ("cost", "budget", "overrun", "actual", "spend", "price", "financial"),
    "procurement": ("procurement", "purchase", "supplier", "vendor", "order", "delivery", "material order"),
    "schedule": ("schedule", "activity", "progress", "milestone", "behind plan", "planned versus", "wbs"),
    "risk": ("risk", "hazard", "mitigation", "exposure", "escalate"),
    "contract": ("contract", "agreement", "expiry", "closeout", "party", "parties", "entitlement"),
    "resource": ("resource", "workforce", "labour", "labor", "equipment utilization", "crew", "manpower"),
    "executive": ("dashboard", "executive", "overview", "health overview", "consolidated"),
    "management": (
        "priority",
        "priorities",
        "action plan",
        "recommend",
        "what should",
        "next action",
        "management",
        "focus",
    ),
    "forecast": ("forecast", "early warning", "warning", "likely", "predict", "future"),
    "performance": ("performance score", "health score", "overall score", "score the project"),
    "monitoring": ("monitor", "on track", "critical", "variance", "performing"),
}


def _is_transient_gemini_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_ERROR_MARKERS)


def _document_context(document_search_tool: Callable[..., Any], message: str) -> str:
    try:
        found = document_search_tool(message)
    except Exception as exc:
        found = {"matches": [], "note": "Document lookup failed: %s" % exc}
    return json.dumps(found, default=str)[:8000]


def _message_matches(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _select_tools_for_message(message: str, catalog: dict[str, Any]) -> list[Any]:
    """Return a focused tool list so free-tier Gemini is less overloaded."""
    text = (message or "").lower()

    # Always available: calculations, project summary, document search.
    selected: list[Any] = [
        *BASE_CONSTRUCTION_TOOLS,
        catalog["summary"],
        catalog["document_search"],
    ]
    seen = {id(tool) for tool in selected}

    def add(key: str) -> None:
        tool = catalog.get(key)
        if tool is None or id(tool) in seen:
            return
        selected.append(tool)
        seen.add(id(tool))

    topic_hits = {
        topic: _message_matches(text, keywords)
        for topic, keywords in _TOOL_TOPIC_KEYWORDS.items()
    }

    if topic_hits["document"]:
        add("document_intelligence")
    if topic_hits["boq"]:
        add("boq")
    if topic_hits["cost"]:
        add("cost")
    if topic_hits["procurement"]:
        add("procurement")
    if topic_hits["schedule"] or topic_hits["monitoring"]:
        add("schedule")
        add("monitoring")
    if topic_hits["risk"]:
        add("risk_analysis")
        add("risk_prediction")
    if topic_hits["contract"]:
        add("contract")
    if topic_hits["resource"]:
        add("resource")
    if topic_hits["executive"]:
        add("executive")
    if topic_hits["management"]:
        add("priorities")
        add("action_plan")
        add("management_recommendations")
    if topic_hits["forecast"]:
        add("forecast")
        add("early_warnings")
    if topic_hits["performance"]:
        add("performance_score")

    # Broad / ambiguous questions: small management default set.
    if len(selected) <= len(BASE_CONSTRUCTION_TOOLS) + 2:
        add("priorities")
        add("monitoring")
        add("executive")
        add("document_intelligence")

    # Hard cap keeps free-tier tool-calling stable.
    max_tools = 10
    if len(selected) > max_tools:
        selected = selected[:max_tools]

    return selected


def _generate_with_model(
    client: genai.Client,
    model_id: str,
    message: str,
    project_id: str,
    tools: list[Any],
    document_search_tool: Callable[..., Any],
):
    context = _document_context(document_search_tool, message)
    chat = client.chats.create(
        model=model_id,
        config=types.GenerateContentConfig(
            system_instruction=CONSTRUCTION_AGENT_SYSTEM,
            temperature=0.2,
            tools=tools,
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

    document_search_tool = make_document_search_tool(db, project_id)
    catalog = {
        "summary": make_project_summary_tool(db, project_id),
        "priorities": make_project_priorities_tool(db, project_id),
        "action_plan": make_project_action_plan_tool(db, project_id),
        "monitoring": make_project_monitoring_tool(db, project_id),
        "risk_analysis": make_project_risk_analysis_tool(db, project_id),
        "forecast": make_project_forecast_tool(db, project_id),
        "early_warnings": make_project_early_warnings_tool(db, project_id),
        "management_recommendations": make_project_management_recommendations_tool(db, project_id),
        "performance_score": make_project_performance_score_tool(db, project_id),
        "cost": make_project_cost_intelligence_tool(db, project_id),
        "procurement": make_project_procurement_intelligence_tool(db, project_id),
        "schedule": make_project_schedule_intelligence_tool(db, project_id),
        "resource": make_project_resource_optimization_tool(db, project_id),
        "boq": make_project_boq_intelligence_tool(db, project_id),
        "document_intelligence": make_project_document_intelligence_tool(db, project_id),
        "executive": make_project_executive_dashboard_tool(db, project_id),
        "contract": make_project_contract_intelligence_tool(db, project_id),
        "risk_prediction": make_project_risk_prediction_tool(db, project_id),
        "document_search": document_search_tool,
    }
    tools = _select_tools_for_message(message, catalog)

    last_error: Exception | None = None

    for index, candidate_model in enumerate(models_to_try):
        try:
            response = _generate_with_model(
                client,
                candidate_model,
                message,
                project_id,
                tools,
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
