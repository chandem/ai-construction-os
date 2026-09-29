"""Unit tests for field diary + progress (Phase 7)."""

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
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "field.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    src = src.replace("from datetime import date\n", "")
    exec(compile(src, "field.py", "exec"), ns)
    return ns


ACTIVITY = {
    "id": "act-1",
    "project_id": "proj-1",
    "code": "A001",
    "name": "Foundations works",
    "work_section": "Foundations",
    "percent_complete": 20,
    "status": "in_progress",
    "planned_start": "2026-10-01",
    "planned_finish": "2026-10-14",
}


def test_diary():
    ns = _load()
    e = ns["build_diary_entry"](
        project_id="proj-1",
        work_summary="Excavation complete on grid A-B",
        weather="clear",
        workforce_on_site=12,
    )
    assert e["project_id"] == "proj-1"
    assert e["status"] == "draft"
    assert e["workforce_on_site"] == 12
    assert e["entry_date"]


def test_progress():
    ns = _load()
    u = ns["build_progress_update"](ACTIVITY, percent_complete=45, note="Formwork started")
    assert u["percent_complete"] == 45.0
    assert u["previous_percent"] == 20.0
    assert u["delta_percent"] == 25.0
    assert u["schedule_activity_id"] == "act-1"


def test_apply_progress():
    ns = _load()
    a = ns["apply_progress_to_activity"](ACTIVITY, 100)
    assert a["percent_complete"] == 100.0
    assert a["status"] == "complete"
    b = ns["apply_progress_to_activity"](ACTIVITY, 50)
    assert b["status"] == "in_progress"


def test_summary():
    ns = _load()
    diary = [ns["build_diary_entry"](project_id="proj-1", work_summary="Day 1")]
    prog = [ns["build_progress_update"](ACTIVITY, percent_complete=40)]
    s = ns["field_summary"](diary, prog, [ACTIVITY])
    assert s["diary_count"] == 1
    assert s["progress_update_count"] == 1
    assert s["overall_percent_complete"] == 20.0  # from activity list


if __name__ == "__main__":
    test_diary()
    test_progress()
    test_apply_progress()
    test_summary()
    print("All field unit tests passed.")
