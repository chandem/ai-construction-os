import json
from typing import Any

from openai import OpenAI

from .config import settings

EXTRACTION_MODEL = "gpt-4.1-mini"
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
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    if not text.strip():
        return {
            "document_type": _fallback_type(filename),
            "confidence": 0.0,
            "summary": "No extractable text was found.",
            "data": {},
            "warnings": ["The document contains no extractable text; OCR may be required."],
        }

    content = text[:MAX_EXTRACTION_CHARS]
    client = OpenAI(api_key=settings.openai_api_key)
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
- For drawings/specifications, prioritize project/title information, dimensions, materials, standards and technical requirements.
- For schedules, prioritize activities, durations, dates, dependencies and milestones.
- For invoices/payments, prioritize supplier, invoice number, dates, amounts, taxes and payment status.
- Put uncertain or incomplete extraction notes in warnings.
- Do not calculate missing values.

DOCUMENT TEXT:
{content}
"""
    response = client.chat.completions.create(
        model=EXTRACTION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    result = json.loads(raw)
    result["document_type"] = result.get("document_type") if result.get("document_type") in CLASSIFICATION_TYPES else _fallback_type(filename)
    try:
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0))))
    except (TypeError, ValueError):
        result["confidence"] = 0.0
    result.setdefault("summary", "")
    result.setdefault("data", {})
    result.setdefault("warnings", [])
    return result
