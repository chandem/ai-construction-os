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


def test_module_status_needs_setup_when_table_is_missing():
    st = module_status(
        module_id="field",
        payload={"data": [], "missing_table": "site_diary_entries", "warning": "Apply supabase/field.sql"},
    )
    assert st["status"] == "needs_setup"


def test_module_status_marks_non_schema_warning_as_error():
    st = module_status(module_id="field", payload={"data": [], "warning": "permission denied"})
    assert st["status"] == "error"
    assert st["message"] == "permission denied"


def test_recommend_actions_prioritizes_design_when_empty():
    mods = [
        module_status(module_id="design", payload={"data": []}),
        module_status(module_id="commercial", payload={"data": []}),
    ]
    actions = recommend_actions(mods)
    assert actions
    assert actions[0]["module"] == "design"


def test_recommend_actions_includes_recovery_for_module_errors():
    failed_field = module_status(
        module_id="field",
        payload={"data": [], "warning": "permission denied"},
    )
    actions = recommend_actions([failed_field])
    field_actions = [action for action in actions if action["module"] == "field"]
    assert field_actions
    assert field_actions[0]["title"] == "Review Field module"
    assert "permission denied" in field_actions[0]["detail"]


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



def test_safe_get_retries_transient_resource_error():
    from app.routes_construction_os import _safe_get

    class Query:
        def __init__(self):
            self.calls = 0

        def select(self, *_args):
            return self

        def eq(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def execute(self):
            self.calls += 1
            if self.calls == 1:
                raise OSError(11, "Resource temporarily unavailable")
            return type("Result", (), {"data": [{"id": "row-1"}]})()

    class Client:
        def __init__(self):
            self.query = Query()

        def table(self, _table):
            return self.query

    client = Client()
    result = _safe_get(client, "material_requirements", "project-1")
    assert result["data"] == [{"id": "row-1"}]
    assert client.query.calls == 2


def test_recommend_actions_sequences_planning_before_tender_and_forecast():
    mods = [
        module_status(module_id="design", payload={"data": [{"id": "estimate-1"}]}),
        module_status(module_id="commercial", payload={"data": []}),
        module_status(module_id="planning", payload={"data": []}),
        module_status(module_id="prediction", payload={"data": []}),
    ]

    actions = recommend_actions(mods)
    by_module = {action["module"]: action for action in actions}

    assert by_module["planning"]["priority"] == 2
    assert by_module["commercial"]["priority"] == 3
    assert by_module["prediction"]["priority"] == 4
    assert actions == sorted(actions, key=lambda action: action["priority"])
