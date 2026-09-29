"""Central AI brain foundation: cross-domain project intelligence snapshot.

Aggregates engineering → commercial → planning → field → quality → prediction
into one structured context object for the assistant and a Brain Center UI.
Deterministic synthesis only — LLM grounding is a later step on this payload.
"""

from __future__ import annotations

from typing import Any

from .quantity_takeoff import _as_float, _round_qty

BRAIN_SOURCE = "cross_domain_snapshot"


def _safe_list(x: Any) -> list:
    return x if isinstance(x, list) else []


def _safe_dict(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def build_project_snapshot(
    *,
    project_id: str,
    project_meta: dict[str, Any] | None = None,
    estimate_summary: dict[str, Any] | None = None,
    element_count: int = 0,
    boq_line_count: int = 0,
    tender_summary: dict[str, Any] | None = None,
    contract_summary: dict[str, Any] | None = None,
    wbs_count: int = 0,
    schedule_activities: list[dict[str, Any]] | None = None,
    procurement_summary: dict[str, Any] | None = None,
    field_summary: dict[str, Any] | None = None,
    quality_summary: dict[str, Any] | None = None,
    gis_summary: dict[str, Any] | None = None,
    prediction_summary: dict[str, Any] | None = None,
    risks: list[dict[str, Any]] | None = None,
    forecasts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Unified cross-domain snapshot for RAG/assistant grounding and Brain UI."""
    acts = _safe_list(schedule_activities)
    complete = sum(1 for a in acts if a.get("status") == "complete")
    delayed = sum(1 for a in acts if a.get("status") == "delayed")
    in_prog = sum(1 for a in acts if a.get("status") == "in_progress")

    est = _safe_dict(estimate_summary)
    pred = _safe_dict(prediction_summary)
    field = _safe_dict(field_summary)
    qual = _safe_dict(quality_summary)
    proc = _safe_dict(procurement_summary)
    gis = _safe_dict(gis_summary)
    tender = _safe_dict(tender_summary)
    contract = _safe_dict(contract_summary)

    domains = {
        "engineering": {
            "element_count": element_count,
            "boq_line_count": boq_line_count,
            "estimate_total": est.get("total_amount"),
            "estimate_currency": est.get("currency"),
            "estimate_line_count": est.get("line_count"),
        },
        "commercial": {
            "tender_package_count": tender.get("package_count") or tender.get("line_count"),
            "contract_count": contract.get("contract_count"),
            "contract_value": contract.get("total_value") or contract.get("baseline_total"),
        },
        "planning": {
            "wbs_count": wbs_count,
            "activity_count": len(acts),
            "activities_complete": complete,
            "activities_delayed": delayed,
            "activities_in_progress": in_prog,
        },
        "procurement": {
            "material_lines": proc.get("material_line_count"),
            "equipment_lines": proc.get("equipment_line_count"),
            "workforce_crews": proc.get("workforce_crew_count"),
            "person_days": proc.get("workforce_person_days"),
        },
        "field": {
            "diary_count": field.get("diary_count"),
            "progress_updates": field.get("progress_update_count"),
            "overall_percent": field.get("overall_percent_complete"),
        },
        "quality": {
            "inspections": qual.get("inspection_count"),
            "ncr_open": qual.get("ncr_open"),
            "incidents_open": qual.get("incidents_open"),
        },
        "gis": {
            "locations": gis.get("location_count"),
            "assets": gis.get("asset_count"),
            "assets_geocoded": gis.get("assets_geocoded"),
        },
        "prediction": {
            "open_risks": pred.get("open_risk_count"),
            "health_score": pred.get("health_score"),
            "cost_at_completion": pred.get("cost_at_completion"),
            "schedule_delay_days": pred.get("schedule_delay_days"),
        },
    }

    return {
        "project_id": project_id,
        "project": project_meta or {},
        "domains": domains,
        "open_risks": [
            {
                "code": r.get("risk_code"),
                "title": r.get("title"),
                "level": r.get("level"),
                "category": r.get("category"),
            }
            for r in _safe_list(risks)[:10]
            if r.get("status") not in ("closed", "cancelled")
        ],
        "forecasts": [
            {
                "type": f.get("forecast_type"),
                "label": f.get("label"),
                "value": f.get("value"),
                "unit": f.get("unit"),
            }
            for f in _safe_list(forecasts)[:5]
        ],
        "source": BRAIN_SOURCE,
    }


def build_insights(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Rule-based cross-domain insights (attention items for the OS)."""
    insights: list[dict[str, Any]] = []
    d = _safe_dict(snapshot.get("domains"))
    eng = _safe_dict(d.get("engineering"))
    plan = _safe_dict(d.get("planning"))
    field = _safe_dict(d.get("field"))
    qual = _safe_dict(d.get("quality"))
    pred = _safe_dict(d.get("prediction"))
    comm = _safe_dict(d.get("commercial"))
    proc = _safe_dict(d.get("procurement"))

    if not eng.get("element_count"):
        insights.append(
            {
                "id": "chain-elements",
                "severity": "info",
                "domain": "engineering",
                "title": "No engineering elements yet",
                "detail": "Upload drawings and extract elements to start the quantity → BOQ → estimate chain.",
                "action": "Open Design Center and process design assets.",
            }
        )
    elif not eng.get("estimate_total") and not eng.get("estimate_line_count"):
        insights.append(
            {
                "id": "chain-estimate",
                "severity": "info",
                "domain": "engineering",
                "title": "Elements present but no estimate",
                "detail": "Generate BOQ and estimate from quantities to unlock commercial and planning.",
                "action": "Design Center → BOQ → Estimate.",
            }
        )

    if eng.get("estimate_line_count") and not plan.get("activity_count"):
        insights.append(
            {
                "id": "chain-planning",
                "severity": "info",
                "domain": "planning",
                "title": "Estimate exists without a schedule",
                "detail": "Build WBS and schedule from estimate work sections.",
                "action": "Planning Center → Generate WBS + schedule.",
            }
        )

    if plan.get("activity_count") and not field.get("progress_updates") and not field.get("diary_count"):
        insights.append(
            {
                "id": "chain-field",
                "severity": "info",
                "domain": "field",
                "title": "Schedule without field records",
                "detail": "Record progress and site diary against activities.",
                "action": "Field Center → Record progress / Submit diary.",
            }
        )

    health = _as_float(pred.get("health_score"))
    if health is not None and health < 50:
        insights.append(
            {
                "id": "health-low",
                "severity": "high",
                "domain": "prediction",
                "title": f"Project health score is low ({health})",
                "detail": "Open risks and progress signals are pulling health down.",
                "action": "Review Prediction Center risks and Field progress.",
            }
        )
    elif health is not None and health < 70:
        insights.append(
            {
                "id": "health-medium",
                "severity": "medium",
                "domain": "prediction",
                "title": f"Project health needs attention ({health})",
                "detail": "Moderate risk or delay pressure on the programme/cost view.",
                "action": "Open Prediction Center and mitigate top risks.",
            }
        )

    open_risks = _as_float(pred.get("open_risks")) or 0
    if open_risks >= 3:
        insights.append(
            {
                "id": "risks-many",
                "severity": "medium",
                "domain": "prediction",
                "title": f"{int(open_risks)} open risks on the register",
                "detail": "Multiple open risks from commercial, schedule, quality, or safety signals.",
                "action": "Prioritise critical/high risks in Prediction Center.",
            }
        )

    delayed = plan.get("activities_delayed") or 0
    if delayed:
        insights.append(
            {
                "id": "schedule-delayed",
                "severity": "high" if delayed >= 3 else "medium",
                "domain": "planning",
                "title": f"{delayed} delayed schedule activities",
                "detail": "Programme items are marked delayed.",
                "action": "Planning + Field: re-sequence or recover progress.",
            }
        )

    ncr_open = qual.get("ncr_open") or 0
    if ncr_open:
        insights.append(
            {
                "id": "quality-ncr",
                "severity": "high" if ncr_open >= 3 else "medium",
                "domain": "quality",
                "title": f"{ncr_open} open NCR(s)",
                "detail": "Non-conformances still open may block handover packages.",
                "action": "Quality Center — close corrective actions.",
            }
        )

    inc_open = qual.get("incidents_open") or 0
    if inc_open:
        insights.append(
            {
                "id": "safety-incidents",
                "severity": "high",
                "domain": "quality",
                "title": f"{inc_open} open incident(s)",
                "detail": "Safety/site incidents require investigation closure.",
                "action": "Quality Center — incidents.",
            }
        )

    if eng.get("estimate_total") and not proc.get("material_lines"):
        insights.append(
            {
                "id": "proc-missing",
                "severity": "info",
                "domain": "procurement",
                "title": "No material requirements generated",
                "detail": "Estimate is available; procurement heuristics can propose materials/plant/labour.",
                "action": "Procurement Center → Generate from estimate.",
            }
        )

    if eng.get("estimate_total") and not comm.get("tender_package_count") and not comm.get("contract_count"):
        insights.append(
            {
                "id": "commercial-missing",
                "severity": "info",
                "domain": "commercial",
                "title": "No tender or contract packages yet",
                "detail": "Commercial packages can be built from estimate work sections.",
                "action": "Commercial Center → generate tender packages.",
            }
        )

    if not insights:
        insights.append(
            {
                "id": "healthy",
                "severity": "info",
                "domain": "brain",
                "title": "No critical cross-domain alerts",
                "detail": "Continue feeding documents, progress, and quality records to keep intelligence current.",
                "action": "Use the assistant for project Q&A with RAG.",
            }
        )

    order = {"high": 0, "medium": 1, "info": 2}
    insights.sort(key=lambda x: order.get(x.get("severity") or "info", 9))
    return insights


def brain_context_text(snapshot: dict[str, Any], insights: list[dict[str, Any]]) -> str:
    """Compact text block suitable for LLM system/context injection."""
    d = _safe_dict(snapshot.get("domains"))
    lines = [
        f"Project intelligence snapshot (source={snapshot.get('source')}).",
        f"Engineering: elements={d.get('engineering', {}).get('element_count')}, "
        f"estimate_total={d.get('engineering', {}).get('estimate_total')}.",
        f"Planning: activities={d.get('planning', {}).get('activity_count')}, "
        f"delayed={d.get('planning', {}).get('activities_delayed')}.",
        f"Field: overall%={d.get('field', {}).get('overall_percent')}, "
        f"diary={d.get('field', {}).get('diary_count')}.",
        f"Quality: open_ncrs={d.get('quality', {}).get('ncr_open')}, "
        f"open_incidents={d.get('quality', {}).get('incidents_open')}.",
        f"Prediction: health={d.get('prediction', {}).get('health_score')}, "
        f"open_risks={d.get('prediction', {}).get('open_risks')}, "
        f"delay_days={d.get('prediction', {}).get('schedule_delay_days')}.",
    ]
    if insights:
        lines.append("Top insights:")
        for i in insights[:5]:
            lines.append(f"- [{i.get('severity')}] {i.get('title')}: {i.get('detail')}")
    return "\n".join(lines)


def brain_summary(snapshot: dict[str, Any], insights: list[dict[str, Any]]) -> dict[str, Any]:
    d = _safe_dict(snapshot.get("domains"))
    high = sum(1 for i in insights if i.get("severity") == "high")
    medium = sum(1 for i in insights if i.get("severity") == "medium")
    return {
        "insight_count": len(insights),
        "high_severity_count": high,
        "medium_severity_count": medium,
        "health_score": _safe_dict(d.get("prediction")).get("health_score"),
        "open_risks": _safe_dict(d.get("prediction")).get("open_risks"),
        "estimate_total": _safe_dict(d.get("engineering")).get("estimate_total"),
        "activity_count": _safe_dict(d.get("planning")).get("activity_count"),
        "overall_percent": _safe_dict(d.get("field")).get("overall_percent"),
        "notes": "Cross-domain synthesis for assistant grounding and management attention.",
    }
