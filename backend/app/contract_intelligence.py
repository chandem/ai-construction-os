"""Read-only AI contract intelligence from recorded contract data."""

from __future__ import annotations

from datetime import date
from typing import Any


def build_contract_intelligence(
    project: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    if not contracts:
        return {
            "project": project,
            "status": "insufficient_data",
            "confidence": "low",
            "contract_count": 0,
            "contracts": [],
            "data_gaps": [
                "No contract records are currently linked to this project."
            ],
            "priorities": [{
                "priority": "high",
                "action": "Register the governing project contract and key contractual parties, dates, value, and status.",
                "reason": "Contract intelligence cannot be assessed from an empty contract register.",
            }],
            "note": "Uploaded contract documents may contain additional obligations and clauses; this tool does not invent them.",
        }

    today = date.today()
    analyzed = []
    gaps = []
    priorities = []

    for row in contracts:
        item = {
            "name": row.get("name") or "Unnamed contract",
            "contract_number": row.get("contract_number"),
            "contractor": row.get("contractor"),
            "client": row.get("client"),
            "start_date": row.get("start_date"),
            "end_date": row.get("end_date"),
            "contract_value": row.get("contract_value"),
            "currency": row.get("currency"),
            "status": row.get("status"),
        }
        missing = [
            key for key in ("contractor", "client", "start_date", "end_date", "contract_value", "status")
            if not row.get(key)
        ]
        item["data_gaps"] = missing

        if missing:
            gaps.append({
                "contract": item["name"],
                "missing_fields": missing,
            })

        end_date = row.get("end_date")
        if end_date:
            try:
                if hasattr(end_date, "year"):
                    remaining = (end_date - today).days
                else:
                    remaining = (date.fromisoformat(str(end_date)) - today).days
                item["days_until_end"] = remaining
                if remaining < 0 and str(row.get("status") or "").lower() not in {"closed", "completed", "terminated"}:
                    priorities.append({
                        "priority": "high",
                        "action": "Review the expired contract status and governing extension or completion records.",
                        "reason": f"Contract '{item['name']}' has an end date in the past but is not recorded as closed or completed.",
                    })
                elif 0 <= remaining <= 60:
                    priorities.append({
                        "priority": "high",
                        "action": "Review upcoming contract expiry, extension, completion, and closeout obligations.",
                        "reason": f"Contract '{item['name']}' reaches its recorded end date within {remaining} days.",
                    })
            except (TypeError, ValueError):
                gaps.append({"contract": item["name"], "missing_fields": ["valid_end_date"]})

        analyzed.append(item)

    if gaps:
        priorities.append({
            "priority": "medium",
            "action": "Complete missing contract register fields and reconcile them against the governing contract documents.",
            "reason": "Incomplete contract records limit reliable contractual analysis.",
        })

    if not priorities:
        priorities.append({
            "priority": "low",
            "action": "Continue monitoring contract status and reconcile register data with governing contract documents.",
            "reason": "No immediate register-based contractual control gap was detected.",
        })

    return {
        "project": project,
        "status": "analyzable",
        "confidence": "moderate" if not gaps else "low",
        "contract_count": len(contracts),
        "contracts": analyzed,
        "data_gaps": gaps[:20],
        "priorities": priorities[:10],
        "note": (
            "This analysis uses only recorded contract-register fields. "
            "It does not determine legal entitlement, interpret clauses, or invent obligations. "
            "Governing contract documents and qualified contractual/legal review remain authoritative."
        ),
    }


def make_project_contract_intelligence_tool(client, project_id: str):
    def get_project_contract_intelligence() -> dict[str, Any]:
        """Analyze recorded contract information for the authorized project."""
        project_result = (
            client.table("projects")
            .select("id,name,code,status")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_result.data:
            raise ValueError("Project not found")

        contracts = (
            client.table("contracts")
            .select(
                "id,name,contract_number,contractor,client,start_date,end_date,"
                "contract_value,currency,status"
            )
            .eq("project_id", project_id)
            .limit(100)
            .execute()
        ).data or []

        return build_contract_intelligence(project_result.data, contracts)

    return get_project_contract_intelligence
