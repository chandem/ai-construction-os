"""Gemini-powered construction tool-calling agent.

The model can choose deterministic Python construction tools. The tools execute
locally; the model only decides which tool is appropriate and explains results.
"""

from __future__ import annotations

from google import genai
from google.genai import types

from .config import settings
from .construction_tools import (
    calculate_concrete_volume,
    calculate_material_balance,
    calculate_project_progress,
)

CONSTRUCTION_AGENT_SYSTEM = """You are the Construction AI Agent inside an AI-first Construction OS.

Use the available construction calculation tools whenever the user asks for:
- concrete volume,
- project progress percentage,
- remaining material quantity.

Do not perform these calculations mentally when a tool is available.
After a tool result, explain the answer briefly and include the key inputs.
Do not invent project-specific facts. If required inputs are missing, ask for them.
For engineering, safety, contractual, or financial decisions, calculations do not
replace review by a qualified professional or the governing project documents.
"""

CONSTRUCTION_TOOLS = [
    calculate_concrete_volume,
    calculate_project_progress,
    calculate_material_balance,
]


def run_construction_agent(message: str, model: str | None = None) -> str:
    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.ai_api_key)
    model_id = model or settings.resolved_chat_model

    response = client.models.generate_content(
        model=model_id,
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=CONSTRUCTION_AGENT_SYSTEM,
            temperature=0.2,
            tools=CONSTRUCTION_TOOLS,
        ),
    )

    return (response.text or "").strip()
