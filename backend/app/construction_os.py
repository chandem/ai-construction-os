"""Construction OS kernel — unified project operating layer (Phase 15).

Sits above domain modules. Builds an OS-level snapshot: module readiness,
cross-cutting health, and recommended next actions for the project team.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

OS_SOURCE = "construction_os"

MODULE_REGISTRY: list[dict[str, Any]] = [
    {"id": "design", "label": "Design & Engineering", "phase": 3, "apis": ["engineering/elements", "engineering/boq", "engineering/estimate", "engineering/design-to-cost"]},
    {"id": "commercial", "label": "Commercial", "phase": 4, "apis": ["commercial/summary", "tender/packages", "contracts"]},
    {"id": "planning", "label": "Planning", "phase": 5, "apis": ["planning/summary", "planning/wbs", "planning/schedule"]},
    {"id": "procurement", "label": "Procurement", "phase": 6, "apis": ["procurement/summary"]},
    {"id": "field", "label": "Field", "phase": 7, "apis": ["field/summary"]},
    {"id": "quality", "label": "Quality & Safety", "phase": 8, "apis": ["quality/summary"]},
    {"id": "gis", "label": "GIS", "phase": 9, "apis": ["gis/summary"]},
    {"id": "prediction", "label": "Prediction", "phase": 10, "apis": ["prediction/summary"]},
    {"id": "brain", "label": "Brain", "phase": 11, "apis": ["brain/insights"]},
    {"id": "integrations", "label": "Integrations", "phase": 12, "apis": ["integrations/summary"]},
    {"id": "ops", "label": "Ops", "phase": 13, "apis": ["ops/summary", "ops/health"]},
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_rows(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            return len(payload["data"])
        if isinstance(payload.get("data"), dict):
            return 1
        if payload.get("warning") or payload.get("error"):
            return 0
        return 1 if payload else 0
    return 0


def module_status(
    *,
    module_id: str,
    payload: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    reg = next((m for m in MODULE_REGISTRY if m["id"] == module_id), None)
    label = reg["label"] if reg else module_id
    if error:
        return {"id": module_id, "label": label, "status": "error", "row_signal": 0, "message": error[:500]}
    if payload is None:
        return {"id": module_id, "label": label, "status": "unknown", "row_signal": 0, "message": "Not loaded"}
    if isinstance(payload, dict) and (payload.get("warning") or payload.get("error")):
        return {
            "id": module_id,
            "label": label,
            "status": "needs_setup",
            "row_signal": 0,
            "message": str(payload.get("warning") or payload.get("error"))[:500],
        }
    n = _count_rows(payload)
    if n == 0:
        return {
            "id": module_id,
            "label": label,
            "status": "empty",
            "row_signal": 0,
            "message": "No records yet — generate or enter data",
        }
    return {"id": module_id, "label": label, "status": "active", "row_signal": n, "message": f"{n} signal(s)"}


def recommend_actions(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {m["id"]: m for m in modules}
    actions: list[dict[str, Any]] = []

    def add(priority: int, module: str, title: str, detail: str) -> None:
        actions.append({"priority": priority, "module": module, "title": title, "detail": detail})

    design = by_id.get("design")
    if design and design["status"] in ("empty", "needs_setup", "unknown"):
        add(1, "design", "Establish engineering baseline", "Upload drawings/specs and generate elements → BOQ → estimate.")
    elif design and design["status"] == "active":
        commercial = by_id.get("commercial")
        if commercial and commercial["status"] in ("empty", "needs_setup", "unknown"):
            add(2, "commercial", "Package the estimate for tender", "Generate tender packages from the estimate chain.")
        planning = by_id.get("planning")
        if planning and planning["status"] in ("empty", "needs_setup", "unknown"):
            add(2, "planning", "Build WBS and schedule", "Generate planning from estimate sections.")

    field = by_id.get("field")
    quality = by_id.get("quality")
    if field and field["status"] == "active" and quality and quality["status"] in ("empty", "unknown"):
        add(3, "quality", "Open quality loop", "Log inspections against field progress.")

    prediction = by_id.get("prediction")
    if prediction and prediction["status"] in ("empty", "unknown"):
        add(3, "prediction", "Run risk & forecast pass", "Generate prediction from schedule, NCRs, and cost signals.")

    ops = by_id.get("ops")
    if ops and ops["status"] == "error":
        add(1, "ops", "Check platform health", "Ops health reported an error — review queue and cost budgets.")

    needs = [m for m in modules if m["status"] == "needs_setup"]
    if needs:
        add(1, "ops", "Apply Supabase schemas", "One or more modules report missing tables — run supabase/*.sql in order.")

    if not actions:
        add(5, "brain", "Review Brain insights", "Modules look active — use Brain and Prediction for oversight.")

    actions.sort(key=lambda a: a["priority"])
    return actions


def build_os_snapshot(
    *,
    project_id: str,
    project_name: str | None = None,
    modules: list[dict[str, Any]] | None = None,
    ops_health: dict[str, Any] | None = None,
    brain_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mods = modules or [module_status(module_id=m["id"]) for m in MODULE_REGISTRY]
    active = sum(1 for m in mods if m.get("status") == "active")
    needs_setup = sum(1 for m in mods if m.get("status") == "needs_setup")
    empty = sum(1 for m in mods if m.get("status") == "empty")
    errors = sum(1 for m in mods if m.get("status") == "error")

    readiness = "cold"
    if active >= 6:
        readiness = "operational"
    elif active >= 3:
        readiness = "forming"
    elif active >= 1:
        readiness = "bootstrap"

    if errors:
        readiness = "blocked"

    actions = recommend_actions(mods)
    health_status = (ops_health or {}).get("status") or "unknown"

    return {
        "project_id": project_id,
        "project_name": project_name or "",
        "source": OS_SOURCE,
        "generated_at": utc_now_iso(),
        "readiness": readiness,
        "module_counts": {
            "total": len(mods),
            "active": active,
            "empty": empty,
            "needs_setup": needs_setup,
            "error": errors,
        },
        "modules": mods,
        "recommended_actions": actions,
        "ops_health_status": health_status,
        "brain": brain_summary or {},
        "notes": (
            "Construction OS snapshot is advisory. "
            "Apply supabase SQL for persistence; AI outputs remain human-reviewed."
        ),
    }


def os_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": snapshot.get("project_id"),
        "readiness": snapshot.get("readiness"),
        "module_counts": snapshot.get("module_counts"),
        "action_count": len(snapshot.get("recommended_actions") or []),
        "top_action": (snapshot.get("recommended_actions") or [{}])[0].get("title"),
        "ops_health_status": snapshot.get("ops_health_status"),
        "generated_at": snapshot.get("generated_at"),
    }
