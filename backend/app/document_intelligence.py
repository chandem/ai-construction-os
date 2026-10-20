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
            "items": [
                {
                    "code": "string or null",
                    "description": "string",
                    "unit": "string or null",
                    "quantity": "number or null",
                    "rate": "number or null",
                    "amount": "number or null",
                    "work_section": "string or null",
                }
            ],
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
- For BOQs, prioritize item code, description, unit, quantity, rate, amount, and work section.
- For contracts, prioritize parties, contract value, currency, start/end dates, duration, payment terms, retention, liquidated damages, obligations.
- For tenders, prioritize employer, submission deadline, eligibility, required documents, evaluation criteria, bid security.
- For drawings/specifications, treat the engineering section as the primary structured output.
- Never invent quantities, rates, or contractual terms that are not in the text.

Document text:
{content}
"""
    # generate_json deliberately uses keyword-only arguments; keep the prompt
    # in the user field and the system instructions separate.
    result = generate_json(system=SYSTEM_PROMPT, user=prompt)
    if not isinstance(result, dict):
        result = {}
    result["document_type"] = (
        result.get("document_type")
        if result.get("document_type") in CLASSIFICATION_TYPES
        else _fallback_type(filename)
    )
    if "confidence" not in result:
        result["confidence"] = 0.5
    if "summary" not in result:
        result["summary"] = ""
    if "data" not in result or not isinstance(result.get("data"), dict):
        result["data"] = {}
    if "warnings" not in result or not isinstance(result.get("warnings"), list):
        result["warnings"] = []
    return result


def analyze_drawing_page(image_bytes: bytes, discipline: str = "general") -> dict[str, Any]:
    prompt = (
        "Analyze this construction drawing page. Return JSON with keys: "
        "summary (string), elements (list of {type, label, notes}), "
        "dimensions (list of strings), materials (list of strings), "
        "risks (list of strings), confidence (0-1). Discipline hint: "
        + discipline
    )
    try:
        return generate_vision_json(
            system=SYSTEM_PROMPT,
            prompt=prompt,
            image_bytes=image_bytes,
        )
    except Exception as exc:
        return {"summary": "Visual analysis unavailable", "error": str(exc)[:300], "confidence": 0.0}
