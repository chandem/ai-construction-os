"""Measured work, engineer certification, approval and payment recording."""
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Body, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .routes import _authenticated_client, _project_for_member

router = APIRouter(prefix="/api/v1")
FIELDS = (
    "id,project_id,payee_type,payee_name,reference,description,unit,"
    "measured_quantity,certified_quantity,unit_rate,gross_amount,deductions,"
    "net_amount,status,measurement_date,engineer_name,certification_note,"
    "certified_by,certified_at,approved_by,approved_at,paid_by,paid_at,"
    "payment_reference,notes,created_by,created_at,updated_at"
)
STATUSES = {"measured", "submitted", "certified", "approved", "paid", "rejected"}


def _number(value, label, *, minimum=Decimal("0")):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=f"{label} must be a valid number.")
    if not number.is_finite() or number < minimum:
        raise HTTPException(status_code=422, detail=f"{label} must be at least {minimum}.")
    return number


@router.get("/projects/{project_id}/payments")
def list_work_payments(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    result = (
        client.table("work_payment_certificates")
        .select(FIELDS)
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data or []}


@router.post("/projects/{project_id}/payments")
def create_work_payment(project_id: str, payload: dict = Body(...), token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    payee_type = payload.get("payee_type")
    if payee_type not in {"contractor", "internal_unit"}:
        raise HTTPException(status_code=422, detail="payee_type must be contractor or internal_unit.")
    payee_name = str(payload.get("payee_name") or "").strip()
    description = str(payload.get("description") or "").strip()
    unit = str(payload.get("unit") or "").strip()
    if not payee_name or not description or not unit:
        raise HTTPException(status_code=422, detail="Payee, work description and unit are required.")
    quantity = _number(payload.get("measured_quantity"), "Measured quantity")
    rate = _number(payload.get("unit_rate"), "Unit rate")
    row = {
        "project_id": project_id,
        "payee_type": payee_type,
        "payee_name": payee_name,
        "reference": str(payload.get("reference") or "").strip() or None,
        "description": description,
        "unit": unit,
        "measured_quantity": float(quantity),
        "certified_quantity": 0,
        "unit_rate": float(rate),
        "gross_amount": 0,
        "deductions": 0,
        "net_amount": 0,
        "status": "measured",
        "measurement_date": payload.get("measurement_date") or date.today().isoformat(),
        "notes": str(payload.get("notes") or "").strip() or None,
        "created_by": user["id"],
    }
    result = client.table("work_payment_certificates").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not save the measured work record.")
    return {"data": result.data[0]}


@router.post("/projects/{project_id}/payments/{payment_id}/action")
def act_on_work_payment(
    project_id: str,
    payment_id: str,
    payload: dict = Body(...),
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    found = (
        client.table("work_payment_certificates")
        .select(FIELDS)
        .eq("id", payment_id)
        .eq("project_id", project_id)
        .limit(1)
        .execute()
    )
    if not found.data:
        raise HTTPException(status_code=404, detail="Payment record not found.")
    row = found.data[0]
    action = payload.get("action")
    now_fields = {}
    if action == "submit":
        if row["status"] != "measured":
            raise HTTPException(status_code=409, detail="Only measured records can be submitted.")
        now_fields = {"status": "submitted"}
    elif action == "certify":
        if row["status"] != "submitted":
            raise HTTPException(status_code=409, detail="Submit the measurement before engineer certification.")
        engineer = str(payload.get("engineer_name") or "").strip()
        note = str(payload.get("certification_note") or "").strip()
        if not engineer:
            raise HTTPException(status_code=422, detail="Engineer name is required for certification.")
        quantity = _number(payload.get("certified_quantity"), "Certified quantity")
        if quantity > _number(row.get("measured_quantity"), "Measured quantity"):
            raise HTTPException(status_code=422, detail="Certified quantity cannot exceed measured quantity.")
        rate = _number(row.get("unit_rate"), "Unit rate")
        gross = quantity * rate
        deductions = _number(payload.get("deductions", 0), "Deductions")
        if deductions > gross:
            raise HTTPException(status_code=422, detail="Deductions cannot exceed the gross amount.")
        now_fields = {
            "status": "certified",
            "certified_quantity": float(quantity),
            "gross_amount": float(gross),
            "deductions": float(deductions),
            "net_amount": float(gross - deductions),
            "engineer_name": engineer,
            "certification_note": note or None,
            "certified_by": user["id"],
            "certified_at": "now()",
        }
    elif action == "approve":
        if row["status"] != "certified":
            raise HTTPException(status_code=409, detail="Only engineer-certified work can be approved.")
        if row.get("certified_by") == user["id"]:
            raise HTTPException(status_code=403, detail="A different authorized user must approve the certificate.")
        now_fields = {"status": "approved", "approved_by": user["id"], "approved_at": "now()"}
    elif action == "pay":
        if row["status"] != "approved":
            raise HTTPException(status_code=409, detail="Only approved certificates can be marked paid.")
        payment_reference = str(payload.get("payment_reference") or "").strip()
        if not payment_reference:
            raise HTTPException(status_code=422, detail="Payment reference is required.")
        now_fields = {
            "status": "paid",
            "payment_reference": payment_reference,
            "paid_by": user["id"],
            "paid_at": "now()",
        }
    elif action == "reject":
        if row["status"] not in {"submitted", "certified"}:
            raise HTTPException(status_code=409, detail="Only submitted or certified records can be rejected.")
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise HTTPException(status_code=422, detail="A rejection reason is required.")
        now_fields = {"status": "rejected", "notes": reason}
    else:
        raise HTTPException(status_code=422, detail="Unsupported action.")

    # PostgREST expects timestamp literals as ordinary ISO values; use Python UTC timestamps.
    from datetime import datetime, timezone
    stamp = datetime.now(timezone.utc).isoformat()
    for key, value in list(now_fields.items()):
        if value == "now()":
            now_fields[key] = stamp
    updated = (
        client.table("work_payment_certificates")
        .update(now_fields)
        .eq("id", payment_id)
        .eq("project_id", project_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=500, detail="The payment record could not be updated.")
    return {"data": updated.data[0]}
