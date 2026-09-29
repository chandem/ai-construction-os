"""Prediction foundation: risk register + simple cost/schedule forecasts.

Chain: estimate + schedule + quality + field signals → risks → forecasts.
Heuristics only — not certified risk models or actuarial forecasts.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

PREDICTION_SOURCE = "prediction_heuristic"

RISK_CATEGORIES = (
    "cost",
    "schedule",
    "quality",
    "safety",
    "procurement",
    "design",
    "external",
    "other",
)
RISK_LEVELS = ("low", "medium", "high", "critical")
RISK_STATUSES = ("open", "mitigating", "accepted", "closed", "cancelled")

FORECAST_TYPES = ("cost_at_completion", "schedule_delay_days", "overall_health")


def _level_from_score(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def build_risk(
    *,
    project_id: str,
    title: str,
    category: str = "other",
    level: str = "medium",
    description: str | None = None,
    signal: str | None = None,
    probability: float | None = None,
    impact: float | None = None,
    mitigation: str | None = None,
    status: str = "open",
) -> dict[str, Any]:
    if category not in RISK_CATEGORIES:
        category = "other"
    if level not in RISK_LEVELS:
        level = "medium"
    if status not in RISK_STATUSES:
        status = "open"
    prob = _as_float(probability)
    imp = _as_float(impact)
    score = None
    if prob is not None and imp is not None:
        score = _round_qty(max(0.0, min(1.0, prob)) * max(0.0, min(1.0, imp)))
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "risk_code": f"RSK-{str(uuid4())[:8].upper()}",
        "title": title or "Risk",
        "category": category,
        "level": level,
        "description": description or "",
        "signal": signal or "",
        "probability": prob,
        "impact": imp,
        "score": score,
        "mitigation": mitigation or "",
        "status": status,
        "source": PREDICTION_SOURCE,
        "properties": {},
    }


def derive_risks_from_signals(
    *,
    project_id: str,
    estimate_summary: dict[str, Any] | None = None,
    schedule_activities: list[dict[str, Any]] | None = None,
    ncrs: list[dict[str, Any]] | None = None,
    incidents: list[dict[str, Any]] | None = None,
    progress_overall: float | None = None,
) -> list[dict[str, Any]]:
    """Rule-based risk proposals from commercial / planning / quality signals."""
    risks: list[dict[str, Any]] = []
    est = estimate_summary or {}
    acts = schedule_activities or []
    ncr_list = ncrs or []
    inc_list = incidents or []

    total = _as_float(est.get("total_amount")) or 0.0
    sections = est.get("by_work_section") or []
    if total > 0 and sections:
        top = max(sections, key=lambda s: float(s.get("total_amount") or 0))
        share = float(top.get("total_amount") or 0) / total
        if share >= 0.4:
            risks.append(
                build_risk(
                    project_id=project_id,
                    title=f"Cost concentration in {top.get('work_section') or 'one section'}",
                    category="cost",
                    level=_level_from_score(share),
                    description=f"~{round(share * 100)}% of estimate in one work section.",
                    signal="estimate_section_concentration",
                    probability=0.6,
                    impact=share,
                    mitigation="Review rates and quantities; consider package split.",
                )
            )

    delayed = [a for a in acts if (a.get("status") or "") == "delayed"]
    if delayed:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(delayed)} delayed schedule activities",
                category="schedule",
                level="high" if len(delayed) >= 3 else "medium",
                description="Activities marked delayed on the programme.",
                signal="schedule_delayed_count",
                probability=0.7,
                impact=min(1.0, 0.2 * len(delayed)),
                mitigation="Re-sequence critical path; add resources.",
            )
        )

    incomplete = [
        a
        for a in acts
        if (a.get("status") or "") not in ("complete", "cancelled")
        and (_as_float(a.get("percent_complete")) or 0) < 50
    ]
    if len(acts) >= 3 and len(incomplete) >= max(2, len(acts) // 2):
        risks.append(
            build_risk(
                project_id=project_id,
                title="Many activities still under 50% complete",
                category="schedule",
                level="medium",
                description=f"{len(incomplete)} of {len(acts)} activities below halfway.",
                signal="schedule_low_progress",
                probability=0.5,
                impact=0.4,
                mitigation="Focus field effort on critical incomplete works.",
            )
        )

    open_ncrs = [n for n in ncr_list if n.get("status") not in ("closed", "cancelled")]
    critical_ncrs = [n for n in open_ncrs if n.get("severity") == "critical"]
    major_ncrs = [n for n in open_ncrs if n.get("severity") == "major"]
    if critical_ncrs:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(critical_ncrs)} critical open NCR(s)",
                category="quality",
                level="critical",
                description="Critical non-conformances still open.",
                signal="ncr_critical_open",
                probability=0.8,
                impact=0.9,
                mitigation="Escalate corrective action; hold related works if needed.",
            )
        )
    elif major_ncrs:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(major_ncrs)} major open NCR(s)",
                category="quality",
                level="high",
                description="Major NCRs remain open.",
                signal="ncr_major_open",
                probability=0.6,
                impact=0.6,
                mitigation="Close corrective actions before handover packages.",
            )
        )
    elif len(open_ncrs) >= 3:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(open_ncrs)} open NCRs",
                category="quality",
                level="medium",
                description="Multiple open non-conformances.",
                signal="ncr_open_count",
                probability=0.5,
                impact=0.4,
                mitigation="Prioritise closure by severity and path criticality.",
            )
        )

    open_inc = [i for i in inc_list if i.get("status") not in ("closed", "cancelled")]
    high_inc = [i for i in open_inc if i.get("severity") in ("high", "critical")]
    if high_inc:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(high_inc)} high-severity open incident(s)",
                category="safety",
                level="critical",
                description="Serious safety incidents still open.",
                signal="incident_high_open",
                probability=0.7,
                impact=0.95,
                mitigation="Stop related work until controls verified.",
            )
        )
    elif open_inc:
        risks.append(
            build_risk(
                project_id=project_id,
                title=f"{len(open_inc)} open incident(s)",
                category="safety",
                level="medium",
                description="Open safety/site incidents.",
                signal="incident_open_count",
                probability=0.4,
                impact=0.5,
                mitigation="Complete investigations and close actions.",
            )
        )

    if progress_overall is not None and progress_overall < 30 and len(acts) >= 2:
        risks.append(
            build_risk(
                project_id=project_id,
                title="Overall field progress under 30%",
                category="schedule",
                level="medium",
                description=f"Reported overall progress ~{progress_overall}%.",
                signal="field_low_overall_pct",
                probability=0.55,
                impact=0.45,
                mitigation="Review programme realism and resource loading.",
            )
        )

    return risks


def build_forecasts(
    *,
    project_id: str,
    estimate_summary: dict[str, Any] | None = None,
    schedule_activities: list[dict[str, Any]] | None = None,
    progress_overall: float | None = None,
    risks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Simple illustrative forecasts from estimate + progress + risk load."""
    est = estimate_summary or {}
    acts = schedule_activities or []
    risk_list = risks or []
    forecasts: list[dict[str, Any]] = []

    baseline = _as_float(est.get("total_amount")) or 0.0
    uplift = 0.0
    for r in risk_list:
        if r.get("status") in ("closed", "cancelled"):
            continue
        if r.get("level") == "critical":
            uplift += 0.04
        elif r.get("level") == "high":
            uplift += 0.02
        elif r.get("level") == "medium":
            uplift += 0.01
    uplift = min(0.25, uplift)
    eac = baseline * (1.0 + uplift) if baseline else None
    forecasts.append(
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "forecast_type": "cost_at_completion",
            "label": "Estimated cost at completion (heuristic)",
            "value": _round_qty(eac) if eac is not None else None,
            "unit": est.get("currency") or "USD",
            "baseline": _round_qty(baseline) if baseline else None,
            "delta": _round_qty(eac - baseline) if eac is not None and baseline else None,
            "confidence": "low",
            "method": "baseline × (1 + risk_uplift)",
            "notes": f"Risk uplift {round(uplift * 100, 1)}% from open risk levels.",
            "source": PREDICTION_SOURCE,
            "properties": {},
        }
    )

    delay_days = len([a for a in acts if a.get("status") == "delayed"]) * 3
    if progress_overall is not None and progress_overall < 40 and acts:
        delay_days += 5
    delay_days += sum(1 for r in risk_list if r.get("category") == "schedule" and r.get("status") == "open") * 2
    forecasts.append(
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "forecast_type": "schedule_delay_days",
            "label": "Indicative programme delay (days)",
            "value": float(delay_days),
            "unit": "days",
            "baseline": 0.0,
            "delta": float(delay_days),
            "confidence": "low",
            "method": "delayed_activities×3 + progress/risk penalties",
            "notes": "Illustrative only — not a critical-path analysis.",
            "source": PREDICTION_SOURCE,
            "properties": {},
        }
    )

    health = 80.0
    health -= min(30.0, sum(10 if r.get("level") == "critical" else 6 if r.get("level") == "high" else 3 for r in risk_list if r.get("status") == "open"))
    if progress_overall is not None:
        if progress_overall < 20:
            health -= 15
        elif progress_overall < 40:
            health -= 8
    health = max(0.0, min(100.0, health))
    forecasts.append(
        {
            "id": str(uuid4()),
            "project_id": project_id,
            "forecast_type": "overall_health",
            "label": "Project health score (heuristic)",
            "value": _round_qty(health),
            "unit": "score",
            "baseline": 100.0,
            "delta": _round_qty(health - 100.0),
            "confidence": "low",
            "method": "start 80 − risk/progress penalties",
            "notes": "Higher is better. Not a financial rating.",
            "source": PREDICTION_SOURCE,
            "properties": {},
        }
    )
    return forecasts


def prediction_summary(
    risks: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
) -> dict[str, Any]:
    open_risks = [r for r in risks if r.get("status") not in ("closed", "cancelled")]
    by_level: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for r in open_risks:
        by_level[r.get("level") or "medium"] = by_level.get(r.get("level") or "medium", 0) + 1
        by_cat[r.get("category") or "other"] = by_cat.get(r.get("category") or "other", 0) + 1
    eac = next((f for f in forecasts if f.get("forecast_type") == "cost_at_completion"), None)
    delay = next((f for f in forecasts if f.get("forecast_type") == "schedule_delay_days"), None)
    health = next((f for f in forecasts if f.get("forecast_type") == "overall_health"), None)
    return {
        "risk_count": len(risks),
        "open_risk_count": len(open_risks),
        "risks_by_level": by_level,
        "risks_by_category": by_cat,
        "forecast_count": len(forecasts),
        "cost_at_completion": eac.get("value") if eac else None,
        "schedule_delay_days": delay.get("value") if delay else None,
        "health_score": health.get("value") if health else None,
        "notes": "Heuristic risks and forecasts from project signals — not certified predictions.",
    }


def persist_risk(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "risk_code": row.get("risk_code"),
        "title": row.get("title"),
        "category": row.get("category"),
        "level": row.get("level"),
        "description": row.get("description"),
        "signal": row.get("signal"),
        "probability": row.get("probability"),
        "impact": row.get("impact"),
        "score": row.get("score"),
        "mitigation": row.get("mitigation"),
        "status": row.get("status") or "open",
        "source": row.get("source") or PREDICTION_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("project_risks").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_risks_batch(client, risks: list[dict[str, Any]]) -> int:
    n = 0
    for r in risks:
        if persist_risk(client, r) is not None:
            n += 1
    return n


def persist_forecast(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "forecast_type": row.get("forecast_type"),
        "label": row.get("label"),
        "value": row.get("value"),
        "unit": row.get("unit"),
        "baseline": row.get("baseline"),
        "delta": row.get("delta"),
        "confidence": row.get("confidence"),
        "method": row.get("method"),
        "notes": row.get("notes"),
        "source": row.get("source") or PREDICTION_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("project_forecasts").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_forecasts_batch(client, forecasts: list[dict[str, Any]]) -> int:
    n = 0
    for f in forecasts:
        if persist_forecast(client, f) is not None:
            n += 1
    return n
