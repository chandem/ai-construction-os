"""AI cost intelligence tools for the Construction AI Agent."""

from __future__ import annotations

from typing import Any

from supabase import Client


def build_project_cost_intelligence(summary: dict[str, Any]) -> dict[str, Any]:
    """Analyze recorded project costs conservatively and read-only."""
    costs = summary.get("costs", {})
    entry_count = int(costs.get("entry_count", 0) or 0)
    totals = costs.get("totals_by_currency", {}) or {}

    if entry_count == 0:
        return {
            "project": summary.get("project", {}),
            "status": "insufficient_data",
            "confidence": "low",
            "entry_count": 0,
            "totals_by_currency": {},
            "findings": [],
            "data_gaps": [
                "No project cost entries are available.",
                "No approved project budget or cost baseline is available.",
            ],
            "recommendations": [
                "Establish the approved project budget or cost baseline.",
                "Start recording actual costs by category, date, currency, and relevant work/activity.",
            ],
            "note": "Cost intelligence is read-only and does not create, modify, or approve financial records.",
        }

    findings: list[dict[str, Any]] = [
        {
            "area": "Recorded cost",
            "finding": f"{entry_count} project cost entr{'y' if entry_count == 1 else 'ies'} are recorded.",
            "severity": "information",
        }
    ]
    data_gaps: list[str] = []
    recommendations: list[str] = []

    if not totals:
        data_gaps.append("Cost entries do not contain usable currency totals.")
    elif len(totals) > 1:
        findings.append({
            "area": "Currency",
            "finding": "Costs are recorded in multiple currencies and should not be combined without an approved conversion basis.",
            "severity": "medium",
        })
        recommendations.append("Review each currency separately or apply an approved project exchange-rate basis before consolidation.")
    else:
        currency, amount = next(iter(totals.items()))
        findings.append({
            "area": "Recorded total",
            "finding": f"Recorded cost total is {amount:,.2f} {currency}.",
            "severity": "information",
        })

    data_gaps.append("No approved budget or cost baseline is available for quantitative variance or overrun analysis.")
    recommendations.append("Compare recorded actual costs against the approved budget once a baseline is available.")

    return {
        "project": summary.get("project", {}),
        "status": "baseline_required",
        "confidence": "moderate" if totals else "low",
        "entry_count": entry_count,
        "totals_by_currency": totals,
        "findings": findings,
        "data_gaps": data_gaps,
        "recommendations": recommendations,
        "note": "Recorded costs are facts from the project ledger; this analysis does not infer an overrun without an approved baseline.",
    }


def make_project_cost_intelligence_tool(client: Client, project_id: str):
    from .project_data import make_project_summary_tool

    get_summary = make_project_summary_tool(client, project_id)

    def get_project_cost_intelligence() -> dict[str, Any]:
        """Analyze recorded project costs, cost controls, and baseline gaps."""
        return build_project_cost_intelligence(get_summary())

    return get_project_cost_intelligence
