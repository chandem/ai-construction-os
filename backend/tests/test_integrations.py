"""Unit tests for integrations connectors / connections / sync jobs (Phase 12)."""

from typing import Any


def _load():
    ns: dict[str, Any] = {
        "Any": Any,
        "uuid4": __import__("uuid").uuid4,
        "datetime": __import__("datetime").datetime,
        "timezone": __import__("datetime").timezone,
    }
    src = open(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app" / "integrations.py")).read()
    src = src.replace("from __future__ import annotations\n", "")
    src = src.replace("from datetime import datetime, timezone\n", "")
    exec(compile(src, "integrations.py", "exec"), ns)
    return ns


def test_catalog():
    ns = _load()
    cat = ns["list_connector_catalog"]()
    assert len(cat) >= 4
    types = {c["type"] for c in cat}
    assert "p6" in types and "bim" in types and "drive" in types and "erp" in types


def test_connection():
    ns = _load()
    c = ns["build_connection"](
        project_id="proj-1",
        connector_type="p6",
        name="Site P6",
        direction="import",
    )
    assert c["connector_type"] == "p6"
    assert c["status"] == "draft"
    assert c["name"] == "Site P6"


def test_sync_job():
    ns = _load()
    c = ns["build_connection"](project_id="p", connector_type="bim")
    job = ns["build_sync_job"](
        project_id="p",
        connection_id=c["id"],
        connector_type="bim",
        target="design_models",
    )
    assert job["status"] == "queued"
    done = ns["simulate_sync_complete"](job, success=True, records=12)
    assert done["status"] == "succeeded"
    assert done["records_processed"] == 12


def test_summary():
    ns = _load()
    conns = [
        ns["build_connection"](project_id="p", connector_type="p6"),
        ns["build_connection"](project_id="p", connector_type="drive", status="connected"),
    ]
    jobs = [
        ns["build_sync_job"](
            project_id="p",
            connection_id=conns[0]["id"],
            connector_type="p6",
            target="schedule",
        )
    ]
    s = ns["integrations_summary"](conns, jobs)
    assert s["connection_count"] == 2
    assert s["job_count"] == 1
    assert s["catalog_count"] >= 4


if __name__ == "__main__":
    test_catalog()
    test_connection()
    test_sync_job()
    test_summary()
    print("All integrations unit tests passed.")
