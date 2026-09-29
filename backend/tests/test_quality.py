"""Unit tests for quality inspections, NCRs, incidents (Phase 8)."""

from typing import Any


def _load():
    ns: dict[str, Any] = {
        "Any": Any,
        "uuid4": __import__("uuid").uuid4,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "quality.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    exec(compile(src, "quality.py", "exec"), ns)
    return ns


def test_inspection():
    ns = _load()
    i = ns["build_inspection"](project_id="p", title="Concrete pour", result="pass")
    assert i["title"] == "Concrete pour"
    assert i["result"] == "pass"


def test_ncr():
    ns = _load()
    n = ns["build_ncr"](project_id="p", title="Rebar spacing", severity="major")
    assert n["severity"] == "major"
    assert n["status"] == "open"


def test_incident():
    ns = _load()
    inc = ns["build_incident"](project_id="p", title="Near miss", severity="low")
    assert inc["status"] == "reported"


def test_summary():
    ns = _load()
    inspections = [ns["build_inspection"](project_id="p", title="I1", result="pass")]
    ncrs = [ns["build_ncr"](project_id="p", title="N1", severity="minor")]
    incidents = [ns["build_incident"](project_id="p", title="X1")]
    s = ns["quality_summary"](inspections, ncrs, incidents)
    assert s["inspection_count"] == 1
    assert s["ncr_open"] == 1
    assert s["incidents_open"] == 1


if __name__ == "__main__":
    test_inspection()
    test_ncr()
    test_incident()
    test_summary()
    print("All quality unit tests passed.")
