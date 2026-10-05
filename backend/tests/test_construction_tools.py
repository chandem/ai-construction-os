from app.construction_tools import (
    calculate_concrete_volume,
    calculate_material_balance,
    calculate_project_progress,
)


def test_concrete_volume():
    assert calculate_concrete_volume(10, 5, 0.2) == 10.0


def test_project_progress():
    assert calculate_project_progress(750, 1000) == 75.0


def test_material_balance():
    assert calculate_material_balance(500, 320) == 180.0


def test_material_balance_never_goes_negative():
    assert calculate_material_balance(300, 450) == 0.0
