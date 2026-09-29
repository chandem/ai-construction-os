"""Unit tests for procurement materials / equipment / workforce (Phase 6)."""

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
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "procurement.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from .quantity_takeoff import _as_float, _round_qty\n", "")
    exec(compile(src, "procurement.py", "exec"), ns)
    return ns


SAMPLE = [
    {
        "id": "e1",
        "work_section": "Concrete works — Foundations",
        "element_type": "foundation",
        "quantity": 100.0,
        "unit": "m3",
        "amount": 18000.0,
    },
    {
        "id": "e2",
        "work_section": "Concrete works — Superstructure",
        "element_type": "column",
        "quantity": 50.0,
        "unit": "m3",
        "amount": 14000.0,
    },
    {
        "id": "e3",
        "work_section": "Concrete works — Superstructure",
        "element_type": "slab",
        "quantity": 500.0,
        "unit": "m2",
        "amount": 47500.0,
    },
]


def test_materials():
    ns = _load()
    mats = ns["build_material_requirements"](SAMPLE, project_id="proj-1")
    assert len(mats) >= 3
    codes = {m["material_code"] for m in mats}
    assert "CONC-C25" in codes or "CONC-C30" in codes
    assert "REBAR-B500" in codes
    conc = next(m for m in mats if m["material_code"] in ("CONC-C25", "CONC-C30"))
    assert conc["quantity"] > 0


def test_equipment():
    ns = _load()
    eq = ns["build_equipment_requirements"](SAMPLE, project_id="proj-1")
    assert len(eq) >= 1
    assert all(e.get("quantity_days", 0) > 0 for e in eq)


def test_workforce():
    ns = _load()
    wf = ns["build_workforce_requirements"](SAMPLE, project_id="proj-1")
    assert len(wf) >= 2
    assert all(w.get("person_days", 0) > 0 for w in wf)


def test_package_summary():
    ns = _load()
    pkg = ns["build_procurement_package"](SAMPLE, project_id="proj-1")
    s = pkg["summary"]
    assert s["material_line_count"] >= 3
    assert s["equipment_line_count"] >= 1
    assert s["workforce_crew_count"] >= 2
    assert s["work_section_count"] == 2


if __name__ == "__main__":
    test_materials()
    test_equipment()
    test_workforce()
    test_package_summary()
    print("All procurement unit tests passed.")
