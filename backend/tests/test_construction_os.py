"""Unit tests for Construction OS kernel (Phase 15)."""
from app.construction_os import (
    MODULE_REGISTRY,
    build_os_snapshot,
    module_status,
    os_summary,
    recommend_actions,
)


def test_registry_has_core_modules():
    ids = {m["id"] for m in MODULE_REGISTRY}
    assert "design" in ids and "ops" in ids and "brain" in ids
    assert len(MODULE_REGISTRY) >= 10


def test_module_status_active_from_list_payload():
    st = module_status(module_id="design", payload={"data": [{"id": "1"}, {"id": "2"}]})
    assert st["status"] == "active"
    assert st["row_signal"] == 2


def test_module_status_needs_setup_on_warning():
    st = module_status(module_id="field", payload={"data": [], "warning": "apply field.sql"})
    assert st["status"] == "needs_setup"


def test_recommend_actions_prioritizes_design_when_empty():
    mods = [
        module_status(module_id="design", payload={"data": []}),
        module_status(module_id="commercial", payload={"data": []}),
    ]
    actions = recommend_actions(mods)
    assert actions
    assert actions[0]["module"] == "design"


def test_build_os_snapshot_readiness():
    mods = [
        module_status(module_id="design", payload={"data": [1, 2, 3]}),
        module_status(module_id="commercial", payload={"data": [1]}),
        module_status(module_id="planning", payload={"data": [1]}),
    ]
    snap = build_os_snapshot(project_id="p1", project_name="Demo", modules=mods)
    assert snap["project_id"] == "p1"
    assert snap["readiness"] in ("bootstrap", "forming", "operational")
    assert os_summary(snap)["action_count"] >= 1
