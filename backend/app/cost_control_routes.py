from fastapi import APIRouter, Depends, HTTPException
from .auth import get_access_token, get_current_user
from .routes import _authenticated_client, _project_for_member

router = APIRouter(prefix="/api/v1")

@router.get("/projects/{project_id}/cost-control")
def list_cost_control(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    try:
        result = client.table("cost_control_items").select("*").eq("project_id", project_id).order("description").execute()
        rows = result.data or []
        for row in rows:
            budget = float(row.get("budget_amount") or 0)
            committed = float(row.get("committed_amount") or 0)
            actual = float(row.get("actual_amount") or 0)
            row["variance"] = budget - actual
            row["commitment_variance"] = budget - committed
        return {"data": rows}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Cost control data is not available yet.") from exc

@router.post("/projects/{project_id}/cost-control/sync")
def sync_cost_control(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    try:
        estimates = client.table("estimate_items").select("*").eq("project_id", project_id).eq("status", "approved").execute().data or []
        procurement = client.table("procurement_items").select("boq_item_id,ordered_quantity,delivered_quantity").eq("project_id", project_id).execute().data or []
        proc = {str(p.get("boq_item_id")): p for p in procurement if p.get("boq_item_id")}
        rows = []
        for e in estimates:
            qty = float(e.get("quantity") or 0)
            rate = float(e.get("unit_rate") or 0)
            budget = float(e.get("amount") or qty * rate)
            p = proc.get(str(e.get("boq_item_id") or ""), {})
            committed = float(p.get("ordered_quantity") or 0) * rate
            actual = float(p.get("delivered_quantity") or 0) * rate
            rows.append({
                "project_id": project_id,
                "boq_item_id": e.get("boq_item_id"),
                "description": e.get("description") or "Cost item",
                "unit": e.get("unit"),
                "budget_quantity": qty,
                "budget_unit_rate": rate,
                "budget_amount": budget,
                "committed_amount": committed,
                "actual_amount": actual,
                "progress_percent": 0,
                "notes": "Actual cost currently uses delivered quantity × approved estimate rate."
            })
        client.table("cost_control_items").delete().eq("project_id", project_id).execute()
        if rows:
            client.table("cost_control_items").insert(rows).execute()
        return {"data": rows, "count": len(rows)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not synchronize cost control from approved estimate.") from exc
