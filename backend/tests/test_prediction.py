"""Unit tests for prediction risks + forecasts (Phase 10)."""

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
        "uuid4": __import__("uuid").uuid4,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "prediction.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    exec(compile(src, "prediction.py", "exec"), ns)
    return ns


def test_derive_risks():
    ns = _load()
    risks = ns["derive_risks_from_signals"](
        project_id="proj-1",
        estimate_summary={
            "total_amount": 100000,
            "by_work_section": [
                {"work_section": "Concrete", "total_amount": 60000},
                {"work_section": "Other", "total_amount": 40000},
            ],
        },
        schedule_activities=[
            {"status": "delayed", "percent_complete": 10},
            {"status": "delayed", "percent_complete": 5},
            {"status": "in_progress", "percent_complete": 20},
        ],
        ncrs=[{"status": "open", "severity": "major"}],
        incidents=[{"status": "reported", "severity": "low"}],
        progress_overall=15,
    )
    assert len(risks) >= 3
    cats = {r["category"] for r in risks}
    assert "cost" in cats or "schedule" in cats


def test_forecasts():
    ns = _load()
    risks = [
        ns["build_risk"](project_id="p", title="R1", level="high", category="cost"),
        ns["build_risk"](project_id="p", title="R2", level="critical", category="schedule"),
    ]
    fc = ns["build_forecasts"](
        project_id="p",
        estimate_summary={"total_amount": 100000, "currency": "USD"},
        schedule_activities=[{"status": "delayed"}, {"status": "in_progress"}],
        progress_overall=25,
        risks=risks,
    )
    assert len(fc) == 3
    eac = next(f for f in fc if f["forecast_type"] == "cost_at_completion")
    assert eac["value"] is not None and eac["value"] > 100000
    delay = next(f for f in fc if f["forecast_type"] == "schedule_delay_days")
    assert delay["value"] >= 3
    health = next(f for f in fc if f["forecast_type"] == "overall_health")
    assert 0 <= health["value"] <= 100


def test_summary():
    ns = _load()
    risks = [ns["build_risk"](project_id="p", title="A", level="high")]
    fc = ns["build_forecasts"](project_id="p", estimate_summary={"total_amount": 50}, risks=risks)
    s = ns["prediction_summary"](risks, fc)
    assert s["open_risk_count"] == 1
    assert s["forecast_count"] == 3


if __name__ == "__main__":
    test_derive_risks()
    test_forecasts()
    test_summary()
    print("All prediction unit tests passed.")
