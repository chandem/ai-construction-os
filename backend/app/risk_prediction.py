"""AI risk prediction from recorded project risk signals."""

from __future__ import annotations

from typing import Any


def build_project_risk_prediction(
    project: dict[str, Any],
    risks: list[dict[str, Any]],
) -> dict[str, Any]:
    level_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    missing_controls: list[dict[str, Any]] = []

    for row in risks:
        level = str(row.get("level") or "unknown").lower()
        status = str(row.get("status") or "unknown").lower()
        level_counts[level] = level_counts.get(level, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

        if level == "high" and (
            not row.get("owner")
            or not row.get("mitigation")
        ):
            missing_controls.append({
                "risk_code": row.get("risk_code"),
                "title": row.get("title") or "Unnamed risk",
                "missing_owner": not bool(row.get("owner")),
                "missing_mitigation": not bool(row.get("mitigation")),
            })

    high_count = level_counts.get("high", 0)
    medium_count = level_counts.get("medium", 0)
    unresolved_high = sum(
        1 for row in risks
        if str(row.get("level") or "").lower() == "high"
        and str(row.get("status") or "").lower() not in {"closed", "resolved", "completed"}
    )

    if not risks:
        return {
            "project": project,
            "status": "insufficient_data",
            "confidence": "low",
            "risk_count": 0,
            "level_counts": level_counts,
            "status_counts": status_counts,
            "predicted_risk_level": "unknown",
            "signals": [],
            "missing_controls": [],
            "priorities": [{
                "priority": "high",
                "action": "Establish and maintain a project risk register before making risk predictions.",
                "reason": "No recorded project risks are available.",
            }],
            "note": "No future risk event is predicted because there are no recorded risk signals.",
        }

    signals = []
    if high_count:
        signals.append({
            "signal": "high_risk_exposure",
            "severity": "high",
            "evidence": f"{high_count} recorded high-level risk(s).",
        })
    if unresolved_high:
        signals.append({
            "signal": "unresolved_high_risks",
            "severity": "high",
            "evidence": f"{unresolved_high} recorded high-level risk(s) are not marked closed, resolved, or completed.",
        })
    if missing_controls:
        signals.append({
            "signal": "risk_control_gaps",
            "severity": "medium",
            "evidence": f"{len(missing_controls)} high-level risk(s) lack an owner or mitigation record.",
        })

    if high_count or unresolved_high:
        predicted_level = "high"
    elif medium_count:
        predicted_level = "medium"
    else:
        predicted_level = "low"

    priorities = []
    if unresolved_high:
        priorities.append({
            "priority": "high",
            "action": "Review unresolved high-level risks and confirm mitigation actions and owners.",
            "reason": f"{unresolved_high} high-level risk(s) remain unresolved or open.",
        })
    if missing_controls:
        priorities.append({
            "priority": "high",
            "action": "Assign owners and document mitigation measures for high-level risks.",
            "reason": "Risk-control information is incomplete.",
        })
    if not priorities:
        priorities.append({
            "priority": "medium",
            "action": "Continue periodic risk reviews and update risk status as project conditions change.",
            "reason": "Recorded risks do not currently show a high-priority control gap.",
        })

    return {
        "project": project,
        "status": "risk_signals_detected",
        "confidence": "moderate",
        "risk_count": len(risks),
        "level_counts": level_counts,
        "status_counts": status_counts,
        "predicted_risk_level": predicted_level,
        "signals": signals,
        "missing_controls": missing_controls[:20],
        "priorities": priorities[:10],
        "note": (
            "This is a rule-based risk signal assessment from recorded project risks. "
            "It does not claim that a future event will occur and does not invent probability, "
            "dates, causes, or risk events that are not recorded."
        ),
    }


def make_project_risk_prediction_tool(client, project_id: str):
    def get_project_risk_prediction() -> dict[str, Any]:
        """Assess recorded risk signals and identify likely risk exposure."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        risks = (
            client.table("project_risks")
            .select("id,risk_code,title,level,status,owner,mitigation")
            .eq("project_id", project_id)
            .limit(1000)
            .execute()
        ).data or []

        return build_project_risk_prediction(project_result.data, risks)

    return get_project_risk_prediction
