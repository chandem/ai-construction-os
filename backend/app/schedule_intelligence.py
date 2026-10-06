"""AI schedule intelligence for recorded project activities."""

from __future__ import annotations

from typing import Any


def build_project_schedule_intelligence(
    project: dict[str, Any],
    activities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze recorded activity progress without inventing dates or schedule facts."""
    activity_count = len(activities)
    analyzed: list[dict[str, Any]] = []
    behind: list[dict[str, Any]] = []
    missing_progress: list[dict[str, Any]] = []

    variances: list[float] = []

    for row in activities:
        name = row.get("name") or row.get("code") or row.get("id") or "Unnamed activity"
        planned_raw = row.get("planned_percent")
        actual_raw = row.get("actual_percent")

        if planned_raw is None or actual_raw is None:
            missing_progress.append({
                "name": name,
                "planned_percent": planned_raw,
                "actual_percent": actual_raw,
            })
            continue

        try:
            planned = float(planned_raw)
            actual = float(actual_raw)
        except (TypeError, ValueError):
            missing_progress.append({
                "name": name,
                "planned_percent": planned_raw,
                "actual_percent": actual_raw,
            })
            continue

        variance = round(actual - planned, 2)
        variances.append(variance)
        item = {
            "name": name,
            "status": row.get("status"),
            "planned_percent": planned,
            "actual_percent": actual,
            "variance_percentage_points": variance,
        }
        analyzed.append(item)
        if variance < 0:
            behind.append(item)

    average_variance = round(sum(variances) / len(variances), 2) if variances else None

    if activity_count == 0:
        status = "insufficient_data"
        confidence = "low"
        headline = "No activities are currently tracked, so schedule performance cannot be measured."
    elif not analyzed:
        status = "insufficient_data"
        confidence = "low"
        headline = "Activities are tracked, but planned and actual progress data is missing or invalid."
    elif average_variance is not None and average_variance < 0:
        status = "attention_required" if average_variance > -10 else "critical"
        confidence = "moderate" if missing_progress else "high"
        headline = (
            f"Average actual progress is {abs(average_variance):.2f} percentage points "
            "below planned progress."
        )
    else:
        status = "on_track"
        confidence = "moderate" if missing_progress else "high"
        headline = (
            "Recorded average actual progress is at or above planned progress."
        )

    priorities: list[dict[str, Any]] = []
    if activity_count == 0:
        priorities.append({
            "priority": "high",
            "action": "Establish the approved activity register and begin regular planned-versus-actual progress updates.",
            "reason": "No activities are currently tracked.",
        })
    elif behind:
        priorities.append({
            "priority": "high" if len(behind) >= max(1, activity_count // 2) else "medium",
            "action": "Review activities behind plan, identify causes, and agree recovery measures with responsible owners.",
            "reason": f"{len(behind)} of {activity_count} tracked activities have negative progress variance.",
        })
    if missing_progress:
        priorities.append({
            "priority": "medium",
            "action": "Complete planned and actual progress fields for activities with missing or invalid schedule data.",
            "reason": f"{len(missing_progress)} activity record(s) cannot be assessed for progress variance.",
        })

    return {
        "project": project,
        "status": status,
        "confidence": confidence,
        "headline": headline,
        "activity_count": activity_count,
        "analyzed_activity_count": len(analyzed),
        "behind_plan_count": len(behind),
        "schedule_variance_percentage_points": average_variance,
        "activities_behind_plan": behind[:20],
        "activities_analyzed": analyzed[:50],
        "data_gaps": [
            "No activities are recorded."
            if activity_count == 0
            else None,
            "Some activities are missing valid planned or actual progress."
            if missing_progress
            else None,
        ],
        "priorities": priorities,
        "note": (
            "This analysis uses only recorded activity progress. It does not infer calendar "
            "delay, planned completion dates, or future outcomes when those fields are unavailable, "
            "and it does not modify project records."
        ),
    }


def make_project_schedule_intelligence_tool(client, project_id: str):
    def get_project_schedule_intelligence() -> dict[str, Any]:
        """Analyze recorded project schedule progress and identify activities behind plan."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        activities = (
            client.table("activities")
            .select("id,name,status,planned_percent,actual_percent")
            .eq("project_id", project_id)
            .limit(1000)
            .execute()
        ).data or []

        result = build_project_schedule_intelligence(project_result.data, activities)
        # Avoid returning null entries in data_gaps to keep the tool output clean.
        result["data_gaps"] = [gap for gap in result["data_gaps"] if gap]
        return result

    return get_project_schedule_intelligence
