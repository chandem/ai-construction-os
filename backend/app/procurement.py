"""Procurement & resources: materials, equipment, workforce from estimate/BOQ chain.

Chain: estimate lines → material requirements → equipment → workforce → procurement summary.
Quantities and crew sizes are illustrative heuristics for planning — not purchase orders.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .quantity_takeoff import _as_float, _round_qty

PROCUREMENT_SOURCE = "estimate_heuristic"

MATERIAL_STATUSES = ("proposed", "requested", "ordered", "delivered", "cancelled")
EQUIPMENT_STATUSES = ("proposed", "reserved", "on_site", "released", "cancelled")
WORKFORCE_STATUSES = ("proposed", "allocated", "active", "complete", "cancelled")

# Material factors per element_type measured unit.
# Each factor: material_code, name, unit, qty_per_measured_unit, category
MATERIAL_FACTORS: dict[str, list[dict[str, Any]]] = {
    "foundation": [
        {"code": "CONC-C25", "name": "Concrete C25/30", "unit": "m3", "factor": 1.0, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 90.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 2.5, "category": "formwork"},
    ],
    "footing": [
        {"code": "CONC-C25", "name": "Concrete C25/30", "unit": "m3", "factor": 1.0, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 80.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 3.0, "category": "formwork"},
    ],
    "column": [
        {"code": "CONC-C30", "name": "Concrete C30/37", "unit": "m3", "factor": 1.0, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 120.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 8.0, "category": "formwork"},
    ],
    "beam": [
        {"code": "CONC-C30", "name": "Concrete C30/37", "unit": "m3", "factor": 1.0, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 110.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 6.0, "category": "formwork"},
    ],
    "slab": [
        {"code": "CONC-C25", "name": "Concrete C25/30", "unit": "m3", "factor": 0.20, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 12.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 1.05, "category": "formwork"},
    ],
    "wall": [
        {"code": "CONC-C25", "name": "Concrete C25/30", "unit": "m3", "factor": 0.25, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 25.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 2.1, "category": "formwork"},
    ],
    "retaining_wall": [
        {"code": "CONC-C30", "name": "Concrete C30/37", "unit": "m3", "factor": 0.35, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 40.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 2.2, "category": "formwork"},
    ],
    "stair": [
        {"code": "CONC-C25", "name": "Concrete C25/30", "unit": "m3", "factor": 1.5, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 150.0, "category": "steel"},
        {"code": "FORM-TIM", "name": "Formwork / shuttering", "unit": "m2", "factor": 12.0, "category": "formwork"},
    ],
    "pipe": [
        {"code": "PIPE-PVC", "name": "Pipe / pipeline material", "unit": "m", "factor": 1.0, "category": "piping"},
        {"code": "BED-SAND", "name": "Bedding sand", "unit": "m3", "factor": 0.15, "category": "earthworks"},
    ],
    "drainage": [
        {"code": "PIPE-DRAIN", "name": "Drainage pipe", "unit": "m", "factor": 1.0, "category": "piping"},
        {"code": "AGG-BASE", "name": "Aggregate bedding", "unit": "m3", "factor": 0.2, "category": "earthworks"},
    ],
    "culvert": [
        {"code": "CONC-C30", "name": "Concrete C30/37", "unit": "m3", "factor": 0.8, "category": "concrete"},
        {"code": "REBAR-B500", "name": "Reinforcement steel", "unit": "kg", "factor": 70.0, "category": "steel"},
    ],
    "road": [
        {"code": "AGG-BASE", "name": "Road base aggregate", "unit": "m3", "factor": 0.3, "category": "earthworks"},
        {"code": "ASPHALT", "name": "Asphalt / surfacing", "unit": "m2", "factor": 1.0, "category": "surfacing"},
    ],
    "pavement": [
        {"code": "AGG-BASE", "name": "Pavement base", "unit": "m3", "factor": 0.25, "category": "earthworks"},
        {"code": "PAVER", "name": "Paving units / concrete", "unit": "m2", "factor": 1.0, "category": "surfacing"},
    ],
    "equipment": [
        {"code": "EQ-ALLOW", "name": "Equipment item (allowance)", "unit": "nos", "factor": 1.0, "category": "equipment_item"},
    ],
    "other": [
        {"code": "MISC", "name": "Miscellaneous materials", "unit": "nos", "factor": 1.0, "category": "other"},
    ],
}

EQUIPMENT_BY_SECTION: list[dict[str, Any]] = [
    {"match": "foundation", "code": "EXC-20T", "name": "Excavator 20t", "unit": "days", "days_per_section": 8},
    {"match": "foundation", "code": "CRANE-50", "name": "Mobile crane 50t", "unit": "days", "days_per_section": 3},
    {"match": "superstructure", "code": "CRANE-50", "name": "Mobile crane 50t", "unit": "days", "days_per_section": 12},
    {"match": "superstructure", "code": "PUMP-CONC", "name": "Concrete pump", "unit": "days", "days_per_section": 6},
    {"match": "wall", "code": "SCAF", "name": "Scaffolding set", "unit": "days", "days_per_section": 10},
    {"match": "road", "code": "ROLLER", "name": "Compactor / roller", "unit": "days", "days_per_section": 5},
    {"match": "road", "code": "GRADER", "name": "Motor grader", "unit": "days", "days_per_section": 4},
    {"match": "drainage", "code": "EXC-08T", "name": "Mini excavator", "unit": "days", "days_per_section": 6},
    {"match": "culvert", "code": "EXC-20T", "name": "Excavator 20t", "unit": "days", "days_per_section": 5},
]

WORKFORCE_CREWS: list[dict[str, Any]] = [
    {"match": "foundation", "trade": "Earthworks crew", "headcount": 6, "days_factor": 0.6},
    {"match": "foundation", "trade": "Concrete crew", "headcount": 8, "days_factor": 0.8},
    {"match": "superstructure", "trade": "Formwork carpenters", "headcount": 10, "days_factor": 0.9},
    {"match": "superstructure", "trade": "Steel fixers", "headcount": 6, "days_factor": 0.7},
    {"match": "superstructure", "trade": "Concrete crew", "headcount": 8, "days_factor": 0.5},
    {"match": "wall", "trade": "Masonry / concrete crew", "headcount": 8, "days_factor": 0.8},
    {"match": "drainage", "trade": "Pipe layers", "headcount": 5, "days_factor": 0.7},
    {"match": "road", "trade": "Paving crew", "headcount": 12, "days_factor": 0.8},
    {"match": "default", "trade": "General labour", "headcount": 6, "days_factor": 0.5},
]

SECTION_DURATION_DEFAULT = 14


def _section_key(row: dict[str, Any]) -> str:
    ws = (row.get("work_section") or row.get("element_type") or "General").strip()
    return ws or "General"


def _et(row: dict[str, Any]) -> str:
    return str(row.get("element_type") or "other").lower().strip()


def build_material_requirements(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
) -> list[dict[str, Any]]:
    """Derive material lines from estimate quantities × factors; aggregate by code+unit."""
    acc: dict[tuple[str, str], dict[str, Any]] = {}
    for row in estimate_lines:
        et = _et(row)
        qty = _as_float(row.get("quantity"))
        if qty is None or qty <= 0:
            continue
        factors = MATERIAL_FACTORS.get(et, MATERIAL_FACTORS["other"])
        section = _section_key(row)
        for f in factors:
            key = (f["code"], f["unit"])
            need = qty * float(f["factor"])
            if key not in acc:
                acc[key] = {
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "material_code": f["code"],
                    "name": f["name"],
                    "category": f["category"],
                    "unit": f["unit"],
                    "quantity": 0.0,
                    "work_sections": set(),
                    "element_types": set(),
                    "source_line_count": 0,
                    "status": "proposed",
                    "source": PROCUREMENT_SOURCE,
                    "properties": {"factor_basis": "element_heuristic"},
                }
            acc[key]["quantity"] += need
            acc[key]["work_sections"].add(section)
            acc[key]["element_types"].add(et)
            acc[key]["source_line_count"] += 1

    materials: list[dict[str, Any]] = []
    for item in sorted(acc.values(), key=lambda x: (x["category"], x["material_code"])):
        item["quantity"] = _round_qty(item["quantity"])
        item["work_sections"] = sorted(item["work_sections"])
        item["element_types"] = sorted(item["element_types"])
        materials.append(item)
    return materials


def build_equipment_requirements(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
) -> list[dict[str, Any]]:
    """Equipment days by matching work section keywords."""
    sections = sorted({_section_key(r) for r in estimate_lines})
    acc: dict[str, dict[str, Any]] = {}
    for section in sections:
        sl = section.lower()
        matched = False
        for eq in EQUIPMENT_BY_SECTION:
            if eq["match"] in sl:
                matched = True
                code = eq["code"]
                if code not in acc:
                    acc[code] = {
                        "id": str(uuid4()),
                        "project_id": project_id,
                        "equipment_code": code,
                        "name": eq["name"],
                        "unit": eq["unit"],
                        "quantity_days": 0,
                        "work_sections": [],
                        "status": "proposed",
                        "source": PROCUREMENT_SOURCE,
                        "properties": {},
                    }
                acc[code]["quantity_days"] += int(eq["days_per_section"])
                if section not in acc[code]["work_sections"]:
                    acc[code]["work_sections"].append(section)
        if not matched:
            code = "PLANT-GEN"
            if code not in acc:
                acc[code] = {
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "equipment_code": code,
                    "name": "General plant allowance",
                    "unit": "days",
                    "quantity_days": 0,
                    "work_sections": [],
                    "status": "proposed",
                    "source": PROCUREMENT_SOURCE,
                    "properties": {},
                }
            acc[code]["quantity_days"] += 5
            if section not in acc[code]["work_sections"]:
                acc[code]["work_sections"].append(section)

    return sorted(acc.values(), key=lambda x: x["equipment_code"])


def build_workforce_requirements(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
    section_duration_days: int = SECTION_DURATION_DEFAULT,
) -> list[dict[str, Any]]:
    """Workforce crews by work section."""
    sections = sorted({_section_key(r) for r in estimate_lines})
    crews: list[dict[str, Any]] = []
    for section in sections:
        sl = section.lower()
        matched_any = False
        for w in WORKFORCE_CREWS:
            if w["match"] == "default":
                continue
            if w["match"] in sl:
                matched_any = True
                days = max(1, int(round(section_duration_days * float(w["days_factor"]))))
                crews.append(
                    {
                        "id": str(uuid4()),
                        "project_id": project_id,
                        "trade": w["trade"],
                        "headcount": int(w["headcount"]),
                        "duration_days": days,
                        "person_days": int(w["headcount"]) * days,
                        "work_section": section,
                        "status": "proposed",
                        "source": PROCUREMENT_SOURCE,
                        "properties": {},
                    }
                )
        if not matched_any:
            w = next(x for x in WORKFORCE_CREWS if x["match"] == "default")
            days = max(1, int(round(section_duration_days * float(w["days_factor"]))))
            crews.append(
                {
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "trade": w["trade"],
                    "headcount": int(w["headcount"]),
                    "duration_days": days,
                    "person_days": int(w["headcount"]) * days,
                    "work_section": section,
                    "status": "proposed",
                    "source": PROCUREMENT_SOURCE,
                    "properties": {},
                }
            )
    return crews


def build_procurement_package(
    estimate_lines: list[dict[str, Any]],
    *,
    project_id: str,
) -> dict[str, Any]:
    """Full procurement package: materials + equipment + workforce + summary."""
    materials = build_material_requirements(estimate_lines, project_id=project_id)
    equipment = build_equipment_requirements(estimate_lines, project_id=project_id)
    workforce = build_workforce_requirements(estimate_lines, project_id=project_id)
    by_category: dict[str, int] = {}
    for m in materials:
        cat = m.get("category") or "other"
        by_category[cat] = by_category.get(cat, 0) + 1
    summary = {
        "material_line_count": len(materials),
        "material_categories": by_category,
        "equipment_line_count": len(equipment),
        "equipment_total_days": sum(int(e.get("quantity_days") or 0) for e in equipment),
        "workforce_crew_count": len(workforce),
        "workforce_person_days": sum(int(w.get("person_days") or 0) for w in workforce),
        "work_section_count": len({_section_key(r) for r in estimate_lines}),
        "notes": (
            "Proposed resource requirements from estimate heuristics. "
            "Not purchase orders or certified resource plans."
        ),
    }
    return {
        "project_id": project_id,
        "materials": materials,
        "equipment": equipment,
        "workforce": workforce,
        "summary": summary,
        "source": PROCUREMENT_SOURCE,
    }


def persist_materials(client, materials: list[dict[str, Any]]) -> int:
    if not materials:
        return 0
    rows = []
    for m in materials:
        rows.append(
            {
                "id": m["id"],
                "project_id": m["project_id"],
                "material_code": m.get("material_code"),
                "name": m.get("name"),
                "category": m.get("category"),
                "unit": m.get("unit"),
                "quantity": m.get("quantity"),
                "work_sections": m.get("work_sections") or [],
                "element_types": m.get("element_types") or [],
                "source_line_count": m.get("source_line_count") or 0,
                "status": m.get("status") or "proposed",
                "source": m.get("source") or PROCUREMENT_SOURCE,
                "properties": m.get("properties") or {},
            }
        )
    try:
        client.table("material_requirements").upsert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def persist_equipment(client, equipment: list[dict[str, Any]]) -> int:
    if not equipment:
        return 0
    rows = []
    for e in equipment:
        rows.append(
            {
                "id": e["id"],
                "project_id": e["project_id"],
                "equipment_code": e.get("equipment_code"),
                "name": e.get("name"),
                "unit": e.get("unit") or "days",
                "quantity_days": e.get("quantity_days"),
                "work_sections": e.get("work_sections") or [],
                "status": e.get("status") or "proposed",
                "source": e.get("source") or PROCUREMENT_SOURCE,
                "properties": e.get("properties") or {},
            }
        )
    try:
        client.table("equipment_requirements").upsert(rows).execute()
        return len(rows)
    except Exception:
        return 0


def persist_workforce(client, workforce: list[dict[str, Any]]) -> int:
    if not workforce:
        return 0
    rows = []
    for w in workforce:
        rows.append(
            {
                "id": w["id"],
                "project_id": w["project_id"],
                "trade": w.get("trade"),
                "headcount": w.get("headcount"),
                "duration_days": w.get("duration_days"),
                "person_days": w.get("person_days"),
                "work_section": w.get("work_section"),
                "status": w.get("status") or "proposed",
                "source": w.get("source") or PROCUREMENT_SOURCE,
                "properties": w.get("properties") or {},
            }
        )
    try:
        client.table("workforce_requirements").upsert(rows).execute()
        return len(rows)
    except Exception:
        return 0
