from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import get_access_token, get_current_user
from .routes import _authenticated_client, _project_for_member
router = APIRouter(prefix="/api/v1")
class ProcurementItemUpdate(BaseModel):
    specification: str | None = Field(default=None, max_length=1000)
    requested_quantity: float | None = Field(default=None, ge=0)
    ordered_quantity: float | None = Field(default=None, ge=0)
    delivered_quantity: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, pattern="^(planned|requested|ordered|partially_delivered|delivered|cancelled)$")
    required_date: str | None = None
    notes: str | None = Field(default=None, max_length=1000)

class ProcurementItemRequest(BaseModel):
    material_name: str = Field(min_length=1, max_length=200)
    specification: str | None = Field(default=None, max_length=1000)
    unit: str | None = Field(default=None, max_length=32)
    required_quantity: float = Field(default=0, ge=0)
    supplier: str | None = Field(default=None, max_length=200)
    status: str = Field(default="planned", pattern="^(planned|requested|ordered|partially_delivered|delivered|cancelled)$")
    required_date: str | None = None
    notes: str | None = Field(default=None, max_length=1000)
@router.get("/projects/{project_id}/procurement/items")
def list_procurement_items(project_id: str, token: str = Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    result=client.table("procurement_items").select("*").eq("project_id",project_id).order("created_at",desc=True).execute()
    return {"data":result.data or []}
@router.post("/projects/{project_id}/procurement/items")
def create_procurement_item(project_id: str,payload: ProcurementItemRequest,token: str=Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    row=payload.model_dump(); row["project_id"]=project_id
    result=client.table("procurement_items").insert(row).execute()
    if not result.data: raise HTTPException(status_code=500,detail="Procurement item was not created.")
    return {"data":result.data[0]}
@router.patch("/projects/{project_id}/procurement/items/{item_id}")
def update_procurement_item(project_id: str, item_id: str, payload: ProcurementItemUpdate, token: str = Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    existing=client.table("procurement_items").select("id").eq("id",item_id).eq("project_id",project_id).maybe_single().execute()
    if not existing.data: raise HTTPException(status_code=404, detail="Procurement item not found.")
    update={k:v for k,v in payload.model_dump().items() if v is not None}
    if not update: raise HTTPException(status_code=400, detail="No procurement changes supplied.")
    current_row=client.table("procurement_items").select("*").eq("id",item_id).eq("project_id",project_id).maybe_single().execute().data
    result=client.table("procurement_items").update(update).eq("id",item_id).eq("project_id",project_id).execute()
    updated=result.data[0] if result.data else {**(current_row or {}), **update}
    old_delivered=float((current_row or {}).get("delivered_quantity") or 0)
    new_delivered=float(updated.get("delivered_quantity") or 0)
    delta=new_delivered-old_delivered
    if delta != 0:
        inv=client.table("inventory_items").select("*").eq("project_id",project_id).eq("procurement_item_id",item_id).maybe_single().execute()
        if inv.data:
            inv_row=inv.data
        else:
            created=client.table("inventory_items").insert({"project_id":project_id,"procurement_item_id":item_id,"item_code":updated.get("item_code"),"material_name":updated.get("material_name") or "Procurement item","specification":updated.get("specification"),"unit":updated.get("unit"),"supplier":updated.get("supplier"),"received_quantity":0}).execute()
            if not created.data: raise HTTPException(status_code=500, detail="Could not create inventory item for delivery.")
            inv_row=created.data[0]
        new_received=float(inv_row.get("received_quantity") or 0)+delta
        client.table("inventory_items").update({"received_quantity":new_received,"supplier":updated.get("supplier"),"updated_at":"now()"}).eq("id",inv_row["id"]).execute()
        client.table("inventory_transactions").insert({"project_id":project_id,"inventory_item_id":inv_row["id"],"procurement_item_id":item_id,"transaction_type":"receipt" if delta>0 else "adjustment","quantity":delta,"reference":updated.get("item_code") or item_id,"notes":"Automatic receipt from procurement delivery update.","created_by":user["id"]}).execute()
    return {"data": updated, "inventory_receipt_quantity": delta}

class InventoryIssueRequest(BaseModel):
    quantity: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=1000)

@router.get("/projects/{project_id}/inventory/items")
def list_inventory_items(project_id: str, token: str = Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    result=client.table("inventory_items").select("*").eq("project_id",project_id).order("material_name").execute()
    return {"data": result.data or []}

@router.patch("/projects/{project_id}/inventory/items/{item_id}")
def update_inventory_item(project_id: str, item_id: str, payload: dict, token: str = Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    allowed={"opening_quantity","consumed_quantity","reserved_quantity","reorder_level","location"}
    update={k:v for k,v in payload.items() if k in allowed and v is not None}
    if not update: raise HTTPException(status_code=400, detail="No inventory changes supplied.")
    existing=client.table("inventory_items").select("id").eq("id",item_id).eq("project_id",project_id).maybe_single().execute()
    if not existing.data: raise HTTPException(status_code=404, detail="Inventory item not found.")
    result=client.table("inventory_items").update(update).eq("id",item_id).eq("project_id",project_id).execute()
    return {"data": result.data[0] if result.data else {**existing.data, **update}}

@router.post("/projects/{project_id}/inventory/items/{item_id}/issue")
def issue_inventory_item(project_id: str, item_id: str, payload: InventoryIssueRequest, token: str = Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    existing=client.table("inventory_items").select("*").eq("id",item_id).eq("project_id",project_id).maybe_single().execute()
    if not existing.data: raise HTTPException(status_code=404, detail="Inventory item not found.")
    row=existing.data
    available=float(row.get("opening_quantity") or 0)+float(row.get("received_quantity") or 0)-float(row.get("consumed_quantity") or 0)-float(row.get("reserved_quantity") or 0)
    if payload.quantity > available: raise HTTPException(status_code=400, detail=f"Insufficient available stock. Available: {available:g} {row.get('unit') or ''}".strip())
    consumed=float(row.get("consumed_quantity") or 0)+payload.quantity
    result=client.table("inventory_items").update({"consumed_quantity":consumed,"updated_at":"now()"}).eq("id",item_id).eq("project_id",project_id).execute()
    client.table("inventory_transactions").insert({"project_id":project_id,"inventory_item_id":item_id,"transaction_type":"issue","quantity":-payload.quantity,"notes":payload.notes or "Material issued for site consumption.","created_by":user["id"]}).execute()
    return {"data": result.data[0] if result.data else {**row,"consumed_quantity":consumed},"issued_quantity":payload.quantity,"remaining_available":available-payload.quantity}

@router.post("/projects/{project_id}/procurement/from-boq")
def create_procurement_from_boq(project_id: str,token: str=Depends(get_access_token)):
    user=get_current_user(token); client=_authenticated_client(token); _project_for_member(project_id,user["id"],client)
    boq=client.table("boq_items").select("id,item_code,description,quantity,unit,status").eq("project_id",project_id).eq("status","approved").execute()
    created=[]
    for item in boq.data or []:
        exists=client.table("procurement_items").select("id").eq("project_id",project_id).eq("boq_item_id",item["id"]).limit(1).execute()
        if exists.data: continue
        result=client.table("procurement_items").insert({"project_id":project_id,"boq_item_id":item["id"],"item_code":item.get("item_code"),"material_name":item.get("description") or item.get("item_code") or "BOQ item","unit":item.get("unit"),"required_quantity":item.get("quantity") or 0,"requested_quantity":item.get("quantity") or 0,"status":"planned"}).execute()
        if result.data: created.append(result.data[0])
    return {"data":created,"created":len(created),"source_approved_boq_lines":len(boq.data or [])}
