"""Unit tests for GIS locations + infrastructure assets (Phase 9)."""

from typing import Any


def _load():
    ns: dict[str, Any] = {
        "Any": Any,
        "uuid4": __import__("uuid").uuid4,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "gis.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    exec(compile(src, "gis.py", "exec"), ns)
    return ns


def test_location():
    ns = _load()
    loc = ns["build_location"](
        project_id="proj-1",
        name="Main site",
        location_type="site",
        latitude=-1.2921,
        longitude=36.8219,
    )
    assert loc["name"] == "Main site"
    assert loc["latitude"] == -1.2921
    assert loc["status"] == "active"


def test_asset():
    ns = _load()
    a = ns["build_infrastructure_asset"](
        project_id="proj-1",
        name="North block",
        asset_type="building",
        geometry_type="polygon",
    )
    assert a["asset_code"].startswith("AST-")
    assert a["asset_type"] == "building"


def test_from_elements():
    ns = _load()
    elements = [
        {"element_type": "column", "name": "C1", "design_asset_id": "d1"},
        {"element_type": "road", "name": "Access road"},
        {"element_type": "pipe", "name": "Storm drain"},
    ]
    assets = ns["assets_from_engineering_elements"](elements, project_id="proj-1")
    assert len(assets) == 3
    types = {a["asset_type"] for a in assets}
    assert "building" in types
    assert "road" in types
    assert "pipeline" in types


def test_summary():
    ns = _load()
    locs = [ns["build_location"](project_id="p", name="Site", latitude=1.0, longitude=2.0)]
    assets = [ns["build_infrastructure_asset"](project_id="p", name="A", latitude=1.0, longitude=2.0)]
    s = ns["gis_summary"](locs, assets)
    assert s["location_count"] == 1
    assert s["locations_geocoded"] == 1
    assert s["asset_count"] == 1
    assert s["assets_geocoded"] == 1


if __name__ == "__main__":
    test_location()
    test_asset()
    test_from_elements()
    test_summary()
    print("All GIS unit tests passed.")
