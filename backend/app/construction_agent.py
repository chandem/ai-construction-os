"""Gemini-powered construction tool-calling agent."""
from __future__ import annotations

from google import genai
from google.genai import types
from supabase import Client

from .config import settings
from .construction_tools import (
    calculate_concrete_volume,
    calculate_material_balance,
    calculate_project_progress,
)
from .project_data import make_project_summary_tool

CONSTRUCTION_AGENT_SYSTEM = """You are the Construction AI Agent inside an AI-first Construction OS.

Use calculation tools for concrete volume, project progress percentage, and remaining
material quantity. Use get_project_summary for current project status, activities,
materials, equipment, costs, or risks.

Do not invent project-specific facts. Use project data for project facts.
If the available data is insufficient, say what is missing.
For engineering, safety, contractual, or financial decisions, calculations do not
replace review by a qualified professional or the governing project documents.
"""

BASE_CONSTRUCTION_TOOLS = [
    calculate_concrete_volume,
    calculate_project_progress,
    calculate_material_balance,
]


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
    project_summary_tool = make_project_summary_tool(db, project_id)

    response = client.models.generate_content(
        model=model_id,
        contents=f"AUTHORIZED PROJECT ID: {project_id}\n\nUSER REQUEST:\n{message}",
        config=types.GenerateContentConfig(
            system_instruction=CONSTRUCTION_AGENT_SYSTEM,
            temperature=0.2,
            tools=[*BASE_CONSTRUCTION_TOOLS, project_summary_tool],
        ),
    )
    return (response.text or "").strip()
