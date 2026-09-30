import json
from typing import Any

from .config import settings
from .gemini_client import generate_json, generate_vision_json

MAX_EXTRACTION_CHARS = 30000

CLASSIFICATION_TYPES = {
    "contract",
    "boq",
    "tender",
    "drawing_specification",
    "schedule",
    "invoice_payment",
    "report",
    "general",
}

SYSTEM_PROMPT = """You are the document intelligence engine for an AI-first Construction OS.
Classify construction documents and extract useful structured facts.
Never invent facts. Only extract information explicitly present in the supplied text.
Use null for unavailable scalar values, [] for unavailable lists.
Preserve original units, currencies, dates and identifiers.
Engineering findings are observations for professional review, not design approval.
Return valid JSON only."""


def _fallback_type(filename: str) -> str:
    name = filename.lower()
    if "boq" in name or "bill of quantity" in name:
        return "boq"
    if "contract" in name or "agreement" in name:
        return "contract"
    if "tender" in name or "bid" in name:
        return "tender"
    if "schedule" in name or "programme" in name or "program" in name:
        return "schedule"
    if "invoice" in name or "payment" in name:
        return "invoice_payment"
    if "drawing" in name or "specification" in name:
        return "drawing_specification"
    return "general"


def extract_construction_data(filename: str, text: str) -> dict[str, Any]:
    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    if not text.strip():
        return {
            "document_type": _fallback_type(filename),
            "confidence": 0.0,
            "summary": "No extractable text was found.",
            "data": {},
            "warnings": [
                "The document contains no extractable text; OCR or visual drawing analysis may be required."
            ],
        }

    content = text[:MAX_EXTRACTION_CHARS]
    schema_hint = {
        "document_type": "one of contract, boq, tender, drawing_specification, schedule, invoice_payment, report, general",
        "confidence": "number from 0 to 1",
        "summary": "short factual summary",
        "data": {
            "project": {},
            "parties": [],
            "financial": {},
            "dates": {},
            "requirements": [],
            "items": [],
            "engineering": {
                "discipline": "architecture, structural, civil, geotechnical, mechanical, electrical, plumbing, fire, or general",
                "drawing_number": "string or null",
                "drawing_title": "string or null",
                "revision": "string or null",
                "scale": "string or null",
                "sheet_size": "string or null",
                "levels": [],
                "dimensions": [],
                "materials": [],
                "standards": [],
                "elements": [],
                "technical_notes": [],
                "design_parameters": {},
                "coordination_items": [],
                "review_findings": [],
            },
            "risks_or_obligations": [],
            "other": {},
        },
        "warnings": [],
    }
    prompt = f"""Classify and extract this construction document.

Filename: {filename}

Return JSON matching this shape:
{json.dumps(schema_hint, indent=2)}

Extraction rules:
- For BOQs, prioritize item code, description, unit, quantity, rate, amount.
- For contracts, prioritize parties, contract value, currency, start/end dates, duration, payment terms, retention, liquidated damages, obligations.
- For tenders, prioritize employer, submission deadline, eligibility, required documents, evaluation criteria, bid security.
- For drawings/specifications, treat the engineering section as the primary structured output.
- Extract levels, dimensions and design parameters with their original units.
- Never invent materials, codes, or quantities.
- Record review findings only as evidence-based observations.
- Put uncertain notes in warnings.

DOCUMENT TEXT:
{content}
"""
    result = generate_json(system=SYSTEM_PROMPT, user=prompt, temperature=0.0)
    result["document_type"] = (
        result.get("document_type")
        if result.get("document_type") in CLASSIFICATION_TYPES
        else _fallback_type(filename)
    )
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0))))
    except (TypeError, ValueError):
        result["confidence"] = 0.0
    result.setdefault("summary", "")
    result.setdefault("data", {})
    if not isinstance(result["data"], dict):
        result["data"] = {}
    result["data"].setdefault("engineering", {})
    result.setdefault("warnings", [])
    return result


def build_visual_analysis_prompt(discipline: str = "general") -> str:
    return f"""Analyze this construction drawing image as a visual engineering assistant.
Discipline: {discipline}
Return JSON only with: elements, dimensions, symbols, findings, confidence, warnings.
Each element should include type, identifier if visible, location_description, and evidence.
Each dimension should include value, unit if visible, and what it measures.
Each symbol should include type, meaning only if clearly identifiable, and evidence.
Findings must be evidence-based observations requiring professional review; never approve a design or declare a structure safe/unsafe.
Do not invent values hidden or unreadable in the image."""


def analyze_drawing_page(image_bytes: bytes, discipline: str = "general") -> dict[str, Any]:
    """Analyze one rendered drawing page with Gemini vision."""
    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    result = generate_vision_json(
        system=(
            "You are a construction drawing visual-analysis engine. "
            "Never invent unreadable information. Findings require professional review."
        ),
        prompt=build_visual_analysis_prompt(discipline),
        image_bytes=image_bytes,
        mime_type="image/png",
        temperature=0.0,
    )
    result.setdefault("elements", [])
    result.setdefault("dimensions", [])
    result.setdefault("symbols", [])
    result.setdefault("findings", [])
    result.setdefault("warnings", [])
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0))))
    except (TypeError, ValueError):
        result["confidence"] = 0.0
    return result
