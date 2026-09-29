"""Unit tests for WBS + schedule planning foundation (Phase 5)."""

from datetime import date
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
        "date": date,
        "timedelta": __import__("datetime").timedelta,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "planning.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    src = src.replace("from datetime import date, timedelta\n", "")
    exec(compile(src, "planning.py", "exec"), ns)
    return ns


SAMPLE = [
    {
        "id": "e1",
        "work_section": "Foundations",
        "element_type": "foundation",
        "quantity": 120.0,
        "amount": 21600.0,
    },
    {
        "id": "e2",
        "work_section": "Structure",
        "element_type": "column",
        "quantity": 45.0,
        "amount": 12600.0,
    },
    {
        "id": "e3",
        "work_section": "Structure",
        "element_type": "slab",
        "quantity": 800.0,
        "amount": 76000.0,
    },
]


def test_build_wbs():
    ns = _load()
    wbs = ns["build_wbs_from_estimate"](SAMPLE, project_id="proj-1", project_name="Demo")
    assert wbs["section_count"] == 2
    assert wbs["node_count"] == 3  # root + 2 sections
    root = wbs["nodes"][0]
    assert root["level"] == 0
    assert root["name"] == "Demo"
    assert root["baseline_amount"] == 110200.0
    sections = {n["name"] for n in wbs["section_nodes"]}
    assert sections == {"Foundations", "Structure"}


def test_build_schedule():
    ns = _load()
    wbs = ns["build_wbs_from_estimate"](SAMPLE, project_id="proj-1")
    sched = ns["build_schedule_from_wbs"](
        wbs, SAMPLE, project_id="proj-1", start_date=date(2026, 10, 1)
    )
    assert sched["activity_count"] == 2
    assert sched["planned_start"] == "2026-10-01"
    acts = sched["activities"]
    assert acts[0]["status"] == "not_started"
    assert acts[0]["duration_days"] >= 3
    # second activity starts after first finishes
    assert acts[1]["planned_start"] > acts[0]["planned_finish"]
    assert acts[1]["predecessor_ids"] == [acts[0]["id"]]


def test_planning_summary():
    ns = _load()
    wbs = ns["build_wbs_from_estimate"](SAMPLE, project_id="proj-1")
    sched = ns["build_schedule_from_wbs"](wbs, SAMPLE, project_id="proj-1")
    summary = ns["planning_summary"](wbs, sched)
    assert summary["wbs_section_count"] == 2
    assert summary["activity_count"] == 2
    assert summary["activities_by_status"]["not_started"] == 2
    assert summary["total_duration_days"] is not None


if __name__ == "__main__":
    test_build_wbs()
    test_build_schedule()
    test_planning_summary()
    print("All planning unit tests passed.")
