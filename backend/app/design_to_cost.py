"""Design-to-cost intelligence from proposed estimate lines.

Surfaces cost drivers, concentration, and simple quantity/rate what-if scenarios.
All figures remain provisional — for design exploration, not tender pricing.
"""

from __future__ import annotations

from typing import Any

from .estimate import DEFAULT_CURRENCY, apply_rates_to_boq_lines, summarize_estimate
from .quantity_takeoff import _as_float, _round_qty


def _pct(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return _round_qty(100.0 * part / whole)


def cost_drivers(estimate_lines: list[dict[str, Any]], *, top_n: int = 5) -> list[dict[str, Any]]:
    """Rank estimate lines by amount (largest cost drivers first)."""
    priced = []
    for line in estimate_lines:
        amount = _as_float(line.get("amount"))
        if amount is None:
            continue
        priced.append(line)
    total = sum(_as_float(l.get("amount")) or 0.0 for l in priced)
    ranked = sorted(priced, key=lambda x: _as_float(x.get("amount")) or 0.0, reverse=True)
    drivers = []
    for line in ranked[:top_n]:
        amount = _as_float(line.get("amount")) or 0.0
        drivers.append(
            {
                "item_code": line.get("item_code"),
                "element_type": line.get("element_type"),
                "work_section": line.get("work_section"),
                "description": line.get("description"),
                "quantity": line.get("quantity"),
                "unit": line.get("unit"),
                "unit_rate": line.get("unit_rate"),
                "amount": amount,
                "share_pct": _pct(amount, total),
                "source_identifiers": (line.get("source_identifiers") or [])[:10],
            }
        )
    return drivers


def section_concentration(estimate_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Work-section share of total cost, sorted by amount desc."""
    summary = summarize_estimate(estimate_lines)
    total = summary.get("total_amount") or 0.0
    sections = []
    for s in summary.get("by_work_section") or []:
        amount = float(s.get("total_amount") or 0.0)
        sections.append(
            {
                "work_section": s["work_section"],
                "line_count": s["line_count"],
                "total_amount": amount,
                "share_pct": _pct(amount, total),
            }
        )
    sections.sort(key=lambda x: x["total_amount"], reverse=True)
    return sections


def pareto_insight(estimate_lines: list[dict[str, Any]], *, threshold_pct: float = 80.0) -> dict[str, Any]:
    """How many top lines account for threshold_pct of total cost."""
    priced = []
    for line in estimate_lines:
        amount = _as_float(line.get("amount"))
        if amount is None or amount <= 0:
            continue
        priced.append((amount, line))
    priced.sort(key=lambda x: x[0], reverse=True)
    total = sum(a for a, _ in priced)
    if total <= 0 or not priced:
        return {
            "threshold_pct": threshold_pct,
            "lines_needed": 0,
            "line_count": 0,
            "cumulative_amount": 0.0,
            "cumulative_share_pct": 0.0,
            "element_types": [],
        }
    cum = 0.0
    types: list[str] = []
    n = 0
    for amount, line in priced:
        cum += amount
        n += 1
        et = str(line.get("element_type") or "other")
        if et not in types:
            types.append(et)
        if _pct(cum, total) >= threshold_pct:
            break
    return {
        "threshold_pct": threshold_pct,
        "lines_needed": n,
        "line_count": len(priced),
        "cumulative_amount": _round_qty(cum),
        "cumulative_share_pct": _pct(cum, total),
        "element_types": types,
    }


def quantity_sensitivity(
    estimate_lines: list[dict[str, Any]],
    *,
    element_type: str,
    quantity_delta_pct: float,
) -> dict[str, Any]:
    """What-if: scale quantity for one element type by delta %, hold rates fixed."""
    et = element_type.lower().strip()
    factor = 1.0 + (quantity_delta_pct / 100.0)
    base_total = 0.0
    scenario_total = 0.0
    touched = 0
    delta_amount = 0.0
    for line in estimate_lines:
        amount = _as_float(line.get("amount")) or 0.0
        base_total += amount
        if str(line.get("element_type") or "").lower() == et:
            qty = _as_float(line.get("quantity"))
            rate = _as_float(line.get("unit_rate"))
            if qty is not None and rate is not None:
                new_qty = qty * factor
                new_amount = _round_qty(new_qty * rate)
                scenario_total += new_amount
                delta_amount += new_amount - amount
                touched += 1
            else:
                scenario_total += amount
        else:
            scenario_total += amount
    base_total = _round_qty(base_total)
    scenario_total = _round_qty(scenario_total)
    return {
        "element_type": et,
        "quantity_delta_pct": quantity_delta_pct,
        "lines_affected": touched,
        "base_total": base_total,
        "scenario_total": scenario_total,
        "delta_amount": _round_qty(delta_amount),
        "delta_pct_of_base": _pct(delta_amount, base_total) if base_total else 0.0,
        "note": (
            f"Provisional: {quantity_delta_pct:+.1f}% quantity on '{et}' "
            "with rates held constant"
        ),
    }


def rate_sensitivity(
    boq_lines: list[dict[str, Any]],
    *,
    project_id: str,
    element_type: str,
    new_unit_rate: float,
) -> dict[str, Any]:
    """What-if: replace unit rate for one element type; recompute estimate."""
    et = element_type.lower().strip()
    base = apply_rates_to_boq_lines(boq_lines, project_id=project_id)
    scenario = apply_rates_to_boq_lines(
        boq_lines, project_id=project_id, rate_overrides={et: new_unit_rate}
    )
    base_sum = summarize_estimate(base)
    scen_sum = summarize_estimate(scenario)
    base_total = float(base_sum.get("total_amount") or 0.0)
    scen_total = float(scen_sum.get("total_amount") or 0.0)
    delta = _round_qty(scen_total - base_total)
    affected = sum(1 for l in scenario if str(l.get("element_type") or "").lower() == et)
    return {
        "element_type": et,
        "new_unit_rate": new_unit_rate,
        "lines_affected": affected,
        "base_total": base_total,
        "scenario_total": scen_total,
        "delta_amount": delta,
        "delta_pct_of_base": _pct(delta, base_total) if base_total else 0.0,
        "note": f"Provisional: unit rate for '{et}' set to {new_unit_rate}",
    }


def design_levers(estimate_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Suggest high-leverage design attention areas from cost concentration."""
    drivers = cost_drivers(estimate_lines, top_n=3)
    levers = []
    for d in drivers:
        et = d.get("element_type") or "other"
        share = d.get("share_pct") or 0.0
        amount = d.get("amount") or 0.0
        if share >= 25:
            priority = "high"
        elif share >= 10:
            priority = "medium"
        else:
            priority = "low"
        levers.append(
            {
                "element_type": et,
                "work_section": d.get("work_section"),
                "amount": amount,
                "share_pct": share,
                "priority": priority,
                "suggestion": (
                    f"Review design quantities and specification for {et} "
                    f"(~{share}% of provisional cost). Small % changes here "
                    f"move total more than low-share items."
                ),
            }
        )
    return levers


def build_design_to_cost(
    estimate_lines: list[dict[str, Any]],
    *,
    boq_lines: list[dict[str, Any]] | None = None,
    project_id: str = "",
    top_n: int = 5,
) -> dict[str, Any]:
    """Full design-to-cost intelligence payload from estimate lines."""
    summary = summarize_estimate(estimate_lines)
    currency = summary.get("currency") or DEFAULT_CURRENCY
    drivers = cost_drivers(estimate_lines, top_n=top_n)
    sections = section_concentration(estimate_lines)
    pareto = pareto_insight(estimate_lines)
    levers = design_levers(estimate_lines)

    scenarios: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for d in drivers[:3]:
        et = str(d.get("element_type") or "")
        if not et or et in seen_types:
            continue
        seen_types.add(et)
        scenarios.append(quantity_sensitivity(estimate_lines, element_type=et, quantity_delta_pct=-10))
        scenarios.append(quantity_sensitivity(estimate_lines, element_type=et, quantity_delta_pct=10))

    rate_scenarios: list[dict[str, Any]] = []
    if boq_lines and project_id and drivers:
        top_et = str(drivers[0].get("element_type") or "")
        top_rate = _as_float(drivers[0].get("unit_rate"))
        if top_et and top_rate is not None:
            rate_scenarios.append(
                rate_sensitivity(
                    boq_lines,
                    project_id=project_id,
                    element_type=top_et,
                    new_unit_rate=_round_qty(top_rate * 0.9),
                )
            )
            rate_scenarios.append(
                rate_sensitivity(
                    boq_lines,
                    project_id=project_id,
                    element_type=top_et,
                    new_unit_rate=_round_qty(top_rate * 1.1),
                )
            )

    return {
        "currency": currency,
        "baseline": summary,
        "cost_drivers": drivers,
        "section_concentration": sections,
        "pareto": pareto,
        "design_levers": levers,
        "quantity_scenarios": scenarios,
        "rate_scenarios": rate_scenarios,
        "disclaimer": (
            "Design-to-cost figures use provisional unit rates and proposed takeoff. "
            "For design exploration only — not a tender estimate or budget approval."
        ),
    }
