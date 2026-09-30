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
    result=client.table("procurement_items").update(update).eq("id",item_id).eq("project_id",project_id).execute()
    return {"data": result.data[0] if result.data else {**existing.data, **update}}

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
