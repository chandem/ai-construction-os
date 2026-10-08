"""Read-only executive dashboard intelligence for the Construction AI Agent."""
from __future__ import annotations

from typing import Any

from supabase import Client

from .boq_intelligence import make_project_boq_intelligence_tool
from .contract_intelligence import make_project_contract_intelligence_tool
from .cost_intelligence import make_project_cost_intelligence_tool
from .document_intelligence_tool import make_project_document_intelligence_tool
from .procurement_intelligence import make_project_procurement_intelligence_tool
from .project_data import (
    make_project_early_warnings_tool,
    make_project_management_recommendations_tool,
    make_project_monitoring_tool,
    make_project_performance_score_tool,
    make_project_summary_tool,
)
from .resource_optimization import make_project_resource_optimization_tool
from .risk_prediction import make_project_risk_prediction_tool
from .schedule_intelligence import make_project_schedule_intelligence_tool


def build_project_executive_dashboard(
    summary: dict[str, Any],
    performance: dict[str, Any],
    monitoring: dict[str, Any],
    early_warnings: dict[str, Any],
    risk_prediction: dict[str, Any],
    cost: dict[str, Any],
    procurement: dict[str, Any],
    schedule: dict[str, Any],
    resources: dict[str, Any],
    boq: dict[str, Any],
    contracts: dict[str, Any],
    documents: dict[str, Any],
    management: dict[str, Any],
) -> dict[str, Any]:
    """Synthesize existing project intelligence into one concise executive view."""
    performance_score = performance.get("score")
    performance_status = performance.get("status")
    monitoring_status = monitoring.get("overall_status")

    priorities: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_priority(priority: str, area: str, action: str, reason: str) -> None:
        key = (area, action)
        if key in seen:
            return
        seen.add(key)
        priorities.append({
            "priority": priority,
            "area": area,
            "action": action,
            "reason": reason,
        })

    for item in management.get("recommendations", [])[:8]:
        add_priority(
            item.get("priority", "medium"),
            item.get("area", "Management"),
            item.get("recommendation", "Review the project signal."),
            item.get("reason", "Recorded project intelligence requires review."),
        )

    for item in early_warnings.get("warnings", [])[:5]:
        severity = item.get("severity", "medium")
        priority = "high" if severity == "high" else severity
        add_priority(
            priority,
            item.get("area", "Early warning"),
            item.get("recommended_action", "Review the warning."),
            item.get("early_warning", "A recorded project signal needs attention."),
        )

    attention = documents.get("attention_items", [])
    if attention:
        add_priority(
            "medium",
            "Documents",
            "Review document-processing issues before relying on affected files for AI decisions.",
            f"{len(attention)} document-processing item(s) require attention.",
        )

    risk_items = risk_prediction.get("predicted_risks", risk_prediction.get("risks", []))
    if risk_items:
        add_priority(
            "high",
            "Risk",
            "Review the highest-priority recorded risk signals and confirm mitigation ownership.",
            "Risk prediction identified recorded risks that may need preventive attention.",
        )

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    priorities.sort(key=lambda item: rank.get(item["priority"], 4))

    health = "insufficient_data"
    if performance_status in {"critical", "at_risk"} or monitoring_status in {"critical", "at_risk"}:
        health = "attention_required"
    elif performance_status in {"stable", "healthy"} and monitoring_status not in {"critical", "at_risk"}:
        health = "stable"
    elif performance_score is not None:
        health = "low_confidence"

    return {
        "project": summary.get("project", {}),
        "executive_health": health,
        "performance": {
            "score": performance_score,
            "status": performance_status,
            "confidence": performance.get("confidence"),
        },
        "management_status": monitoring_status,
        "key_signals": {
            "schedule": schedule,
            "cost": cost,
            "procurement": procurement,
            "resources": resources,
            "risks": risk_prediction,
            "boq": boq,
            "contracts": contracts,
            "documents": documents,
        },
        "top_priorities": priorities[:10],
        "early_warning_count": early_warnings.get("warning_count", 0),
        "data_gaps": performance.get("data_gaps", []),
        "executive_summary": (
            "This dashboard consolidates read-only project intelligence from the current "
            "project registers. It is a decision-support view, not an approval or certification."
        ),
        "note": (
            "Do not treat missing data as zero performance. Do not invent schedule dates, "
            "cost overruns, procurement shortages, contract obligations, BOQ quantities, or "
            "document correctness. Validate material decisions against approved project records "
            "and qualified professional judgment."
        ),
    }


def make_project_executive_dashboard_tool(client: Client, project_id: str):
    """Create the consolidated executive dashboard tool for one authorized project."""
    summary_tool = make_project_summary_tool(client, project_id)
    performance_tool = make_project_performance_score_tool(client, project_id)
    monitoring_tool = make_project_monitoring_tool(client, project_id)
    early_warnings_tool = make_project_early_warnings_tool(client, project_id)
    risk_prediction_tool = make_project_risk_prediction_tool(client, project_id)
    cost_tool = make_project_cost_intelligence_tool(client, project_id)
    procurement_tool = make_project_procurement_intelligence_tool(client, project_id)
    schedule_tool = make_project_schedule_intelligence_tool(client, project_id)
    resource_tool = make_project_resource_optimization_tool(client, project_id)
    boq_tool = make_project_boq_intelligence_tool(client, project_id)
    contract_tool = make_project_contract_intelligence_tool(client, project_id)
    document_tool = make_project_document_intelligence_tool(client, project_id)
    management_tool = make_project_management_recommendations_tool(client, project_id)

    def get_project_executive_dashboard() -> dict[str, Any]:
        """Return a consolidated, read-only executive view of the project."""
        summary = summary_tool()
        return build_project_executive_dashboard(
            summary=summary,
            performance=performance_tool(),
            monitoring=monitoring_tool(),
            early_warnings=early_warnings_tool(),
            risk_prediction=risk_prediction_tool(),
            cost=cost_tool(),
            procurement=procurement_tool(),
            schedule=schedule_tool(),
            resources=resource_tool(),
            boq=boq_tool(),
            contracts=contract_tool(),
            documents=document_tool(),
            management=management_tool(),
        )

    return get_project_executive_dashboard
