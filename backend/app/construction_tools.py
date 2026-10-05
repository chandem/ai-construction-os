"""Deterministic construction calculation tools for the AI Construction OS.

These functions are intentionally free of LLM logic. An AI agent can call them
when a user asks for a construction calculation, while the calculation itself
remains deterministic and testable.
"""

from __future__ import annotations


def calculate_concrete_volume(length_m: float, width_m: float, depth_m: float) -> float:
    """Return concrete volume in cubic metres."""
    if length_m < 0 or width_m < 0 or depth_m < 0:
        raise ValueError("Dimensions cannot be negative.")
    return round(length_m * width_m * depth_m, 3)


def calculate_project_progress(completed: float, total: float) -> float:
    """Return project progress as a percentage."""
    if total <= 0:
        raise ValueError("Total quantity must be greater than zero.")
    if completed < 0:
        raise ValueError("Completed quantity cannot be negative.")
    if completed > total:
        raise ValueError("Completed quantity cannot exceed total quantity.")
    return round((completed / total) * 100, 2)


def calculate_material_balance(required: float, available: float) -> float:
    """Return the remaining material quantity required."""
    if required < 0 or available < 0:
        raise ValueError("Material quantities cannot be negative.")
    return round(max(required - available, 0), 3)


CONSTRUCTION_TOOLS = {
    "calculate_concrete_volume": calculate_concrete_volume,
    "calculate_project_progress": calculate_project_progress,
    "calculate_material_balance": calculate_material_balance,
}
