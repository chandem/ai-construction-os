"""Unit tests for central brain snapshot + insights (Phase 11)."""

from typing import Any


def _as_float(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def _round_qty(v):
    return round(float(v), 2) if v is not None else None


def _load():
    ns: dict[str, Any] = {
        "_as_float": _as_float,
        "_round_qty": _round_qty,
        "Any": Any,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "brain.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    exec(compile(src, "brain.py", "exec"), ns)
    return ns


def test_snapshot_and_insights():
    ns = _load()
    snap = ns["build_project_snapshot"](
        project_id="proj-1",
        project_meta={"name": "Demo"},
        estimate_summary={"total_amount": 100000, "currency": "USD", "line_count": 10},
        element_count=25,
        boq_line_count=12,
        schedule_activities=[
            {"status": "delayed"},
            {"status": "in_progress"},
            {"status": "complete"},
        ],
        field_summary={"diary_count": 0, "progress_update_count": 0, "overall_percent_complete": 20},
        quality_summary={"inspection_count": 1, "ncr_open": 2, "incidents_open": 1},
        prediction_summary={
            "open_risk_count": 4,
            "health_score": 45,
            "cost_at_completion": 110000,
            "schedule_delay_days": 8,
        },
        risks=[{"risk_code": "RSK-1", "title": "Delay", "level": "high", "category": "schedule", "status": "open"}],
        forecasts=[{"forecast_type": "overall_health", "label": "Health", "value": 45, "unit": "score"}],
    )
    assert snap["domains"]["engineering"]["element_count"] == 25
    assert snap["domains"]["planning"]["activities_delayed"] == 1
    insights = ns["build_insights"](snap)
    assert len(insights) >= 2
    severities = {i["severity"] for i in insights}
    assert "high" in severities or "medium" in severities
    text = ns["brain_context_text"](snap, insights)
    assert "Project intelligence" in text
    summary = ns["brain_summary"](snap, insights)
    assert summary["insight_count"] == len(insights)
    assert summary["health_score"] == 45


def test_empty_chain_insights():
    ns = _load()
    snap = ns["build_project_snapshot"](project_id="p", element_count=0)
    insights = ns["build_insights"](snap)
    assert any(i["id"] == "chain-elements" for i in insights)


if __name__ == "__main__":
    test_snapshot_and_insights()
    test_empty_chain_insights()
    print("All brain unit tests passed.")
