"""Integrations foundation: connector catalog, connections, sync jobs.

Supports P6, BIM, Google Drive / SharePoint, and ERP-style connectors.
Foundation stores config + sync status — live OAuth and API clients are later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

INTEGRATION_SOURCE = "integrations_ops"

CONNECTOR_TYPES = ("p6", "bim", "drive", "sharepoint", "erp", "other")
CONNECTION_STATUSES = ("draft", "connected", "error", "disabled", "archived")
SYNC_DIRECTIONS = ("import", "export", "bidirectional")
SYNC_STATUSES = ("idle", "queued", "running", "succeeded", "failed", "cancelled")
SYNC_TARGETS = (
    "schedule",
    "wbs",
    "documents",
    "design_models",
    "cost",
    "materials",
    "resources",
    "other",
)

# Catalog of supported connectors (metadata only — no live credentials)
CONNECTOR_CATALOG: list[dict[str, Any]] = [
    {
        "type": "p6",
        "name": "Oracle Primavera P6",
        "description": "Import / export WBS and schedule activities.",
        "default_targets": ["wbs", "schedule"],
        "auth_mode": "api_token",
        "docs_hint": "P6 EPPM or P6 Professional XER/XML exchange.",
    },
    {
        "type": "bim",
        "name": "BIM / IFC models",
        "description": "Link design models and element quantities from BIM.",
        "default_targets": ["design_models"],
        "auth_mode": "file_or_api",
        "docs_hint": "IFC / Revit / Navisworks connectors (file upload or cloud API).",
    },
    {
        "type": "drive",
        "name": "Google Drive",
        "description": "Sync project documents and drawings from Drive folders.",
        "default_targets": ["documents"],
        "auth_mode": "oauth",
        "docs_hint": "OAuth client for Drive file list and download.",
    },
    {
        "type": "sharepoint",
        "name": "Microsoft SharePoint / OneDrive",
        "description": "Document libraries for drawings and submittals.",
        "default_targets": ["documents"],
        "auth_mode": "oauth",
        "docs_hint": "Microsoft Graph site/drive permissions.",
    },
    {
        "type": "erp",
        "name": "ERP (cost / procurement)",
        "description": "Push estimate packages and material requirements; pull actuals.",
        "default_targets": ["cost", "materials", "resources"],
        "auth_mode": "api_token",
        "docs_hint": "Generic REST adapter (SAP / Dynamics / custom ERP).",
    },
]


def list_connector_catalog() -> list[dict[str, Any]]:
    return list(CONNECTOR_CATALOG)


def build_connection(
    *,
    project_id: str,
    connector_type: str,
    name: str | None = None,
    direction: str = "import",
    external_ref: str | None = None,
    config: dict[str, Any] | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    if connector_type not in CONNECTOR_TYPES:
        connector_type = "other"
    if direction not in SYNC_DIRECTIONS:
        direction = "import"
    if status not in CONNECTION_STATUSES:
        status = "draft"
    catalog = next((c for c in CONNECTOR_CATALOG if c["type"] == connector_type), None)
    display = name or (catalog["name"] if catalog else connector_type.upper())
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "connector_type": connector_type,
        "name": display,
        "direction": direction,
        "external_ref": external_ref or "",
        "status": status,
        "config": config or {},
        "last_sync_at": None,
        "last_sync_status": "idle",
        "source": INTEGRATION_SOURCE,
        "properties": {
            "default_targets": (catalog or {}).get("default_targets") or [],
            "auth_mode": (catalog or {}).get("auth_mode") or "api_token",
        },
    }


def build_sync_job(
    *,
    project_id: str,
    connection_id: str,
    connector_type: str,
    target: str = "other",
    direction: str = "import",
    status: str = "queued",
    message: str | None = None,
) -> dict[str, Any]:
    if target not in SYNC_TARGETS:
        target = "other"
    if direction not in SYNC_DIRECTIONS:
        direction = "import"
    if status not in SYNC_STATUSES:
        status = "queued"
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "connection_id": connection_id,
        "connector_type": connector_type,
        "target": target,
        "direction": direction,
        "status": status,
        "message": message
        or (
            "Queued — live connector runtime not configured in this foundation. "
            "Job records progress for later workers."
        ),
        "started_at": now if status == "running" else None,
        "finished_at": None,
        "records_processed": 0,
        "source": INTEGRATION_SOURCE,
        "properties": {},
    }


def simulate_sync_complete(job: dict[str, Any], *, success: bool = True, records: int = 0) -> dict[str, Any]:
    """Mark a job finished (used when no live connector worker exists)."""
    updated = dict(job)
    now = datetime.now(timezone.utc).isoformat()
    updated["status"] = "succeeded" if success else "failed"
    updated["finished_at"] = now
    updated["started_at"] = updated.get("started_at") or now
    updated["records_processed"] = records
    if success:
        updated["message"] = (
            f"Simulated sync complete ({records} records). "
            "Connect live P6/BIM/Drive/ERP credentials to process real data."
        )
    else:
        updated["message"] = "Simulated sync failed — check connector configuration."
    return updated


def integrations_summary(
    connections: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for c in connections:
        t = c.get("connector_type") or "other"
        by_type[t] = by_type.get(t, 0) + 1
        s = c.get("status") or "draft"
        by_status[s] = by_status.get(s, 0) + 1
    job_by_status: dict[str, int] = {}
    for j in jobs:
        s = j.get("status") or "idle"
        job_by_status[s] = job_by_status.get(s, 0) + 1
    return {
        "connection_count": len(connections),
        "connections_by_type": by_type,
        "connections_by_status": by_status,
        "job_count": len(jobs),
        "jobs_by_status": job_by_status,
        "catalog_count": len(CONNECTOR_CATALOG),
        "notes": (
            "Integration foundation stores connections and sync jobs. "
            "Live OAuth/API workers are Phase 12 hardening."
        ),
    }


def persist_connection(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "connector_type": row.get("connector_type"),
        "name": row.get("name"),
        "direction": row.get("direction"),
        "external_ref": row.get("external_ref"),
        "status": row.get("status") or "draft",
        "config": row.get("config") or {},
        "last_sync_at": row.get("last_sync_at"),
        "last_sync_status": row.get("last_sync_status") or "idle",
        "source": row.get("source") or INTEGRATION_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("integration_connections").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_sync_job(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "connection_id": row.get("connection_id"),
        "connector_type": row.get("connector_type"),
        "target": row.get("target"),
        "direction": row.get("direction"),
        "status": row.get("status") or "queued",
        "message": row.get("message"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "records_processed": row.get("records_processed") or 0,
        "source": row.get("source") or INTEGRATION_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("integration_sync_jobs").upsert(payload).execute()
        return payload
    except Exception:
        return None
