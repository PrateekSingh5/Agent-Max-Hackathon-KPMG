from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from pathlib import Path
from typing import List, Optional, Any, Dict

import fastapi as _fastapi
from sqlalchemy import orm as _orm

import schema as _schema
import services as _services
import db_utils as _db_utils
import agent as _agent
import os
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
import utils as mail_utils

# SINGLE FastAPI INSTANCE
app = _fastapi.FastAPI()

# Globals preserved from your previous code
LAST_EMP_ID: Optional[str] = None
EMP_DETAILS: List[Dict[str, Any]] = []

OUT_DIR = Path(os.environ.get("OUT_DIR", "./output/langchain_json"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Attach CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Employee basic info using LAST_EMP_ID
# -------------------------------------------------
@app.get("/api/employee_details")
def get_employee_details():
    global EMP_DETAILS
    if not LAST_EMP_ID:
        raise HTTPException(status_code=404, detail="No emp_id found. Call a route that sets it first.")
    EMP_DETAILS = _db_utils.get_employee_details(LAST_EMP_ID)
    if not EMP_DETAILS:
        raise HTTPException(status_code=404, detail=f"No employee found for id '{LAST_EMP_ID}'")
    return EMP_DETAILS

# -------------------------------------------------
# DB-backed claim creation
# -------------------------------------------------
@app.post("/api/InvoiceData", response_model=_schema.ExpenseClaims)
async def create_expense_claims(
    expense_claims: _schema.createExpenseClaims,
    db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    return await _services.create_expense_claims(expense_claims=expense_claims, db=db)

# -------------------------------------------------
# Legacy "extractor only" debug endpoint
# -------------------------------------------------
@app.post("/api/ExtractorAgent")
async def extractor_agent(
    image_name: str = Query(..., description="Name of the image file"),
    emp_id: str = Query(..., description="Enter Employee ID"),
    json_out_dir: str = Query(..., description="Directory to save JSON output"),
    save_json_file: bool = Query(..., description="Flag to save JSON file"),
):
    state = {
        "file_path": image_name,
        "employee_id_hint": emp_id,
        "json_out_dir": json_out_dir,
        "save_json_file": save_json_file,
    }
    final_state = _agent.extract_node(state)
    return final_state

# -------------------------------------------------
# Unified Agent endpoint (extract / validate / full)
# -------------------------------------------------
@app.post("/api/Agent", response_class=JSONResponse, status_code=status.HTTP_200_OK)
async def agent_router(
    request: Request,
    image_name: str | None = Query(default=None, description="Path to file on server (image/pdf)"),
    emp_id: str | None = Query(default=None, description="Employee ID"),
    json_out_dir: str = Query(default="./output/langchain_json", description="Directory to save JSON"),
    save_json_file: bool = Query(default=True, description="Save extracted JSON file"),
    phase: str = Query(default="extract", description="extract | validate | full"),
):
    global LAST_EMP_ID
    phase = (phase or "extract").lower()

    # try read request body as dict
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = None
    except Exception:
        body = None

    if emp_id:
        LAST_EMP_ID = emp_id

    query_map = {
        "image_name": image_name,
        "emp_id": emp_id,
        "json_out_dir": json_out_dir,
        "save_json_file": save_json_file,
        "phase": phase,
    }

    def pick(field_name: str, *fallbacks):
        val = query_map.get(field_name)
        if val is not None:
            return val
        if body and (field_name in body) and (body[field_name]) is not None:
            return body[field_name]
        for fb in fallbacks:
            if fb is not None:
                return fb
        return None

    # --------- VALIDATE ONLY ---------
    if phase == "validate":
        if not body:
            raise HTTPException(status_code=400, detail="Expected JSON body for phase=validate")

        try:
            inv = _agent.InvoicePayload(**body)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

        if not inv.employee_id:
            raise HTTPException(status_code=400, detail="employee_id is required in the payload")

        payload_dict = inv.model_dump(mode="python")

        employee_details_list = _db_utils.get_employee_details(inv.employee_id)
        employee_row = employee_details_list[0] if employee_details_list else None
        if not employee_row:
            result = {
                "tag": "Rejected",
                "decision": "Reject",
                "message": f"Employee '{inv.employee_id}' not found",
                "metrics": None,
                "rule_band": "no_policy"
            }
            return JSONResponse(content=jsonable_encoder({
                "tag": result["tag"],
                "decision": result["decision"],
                "comments": result["message"],
                "validation": result
            }), status_code=200)

        emp_grade = employee_row.get("grade")
        if not emp_grade:
            result = {
                "tag": "Pending",
                "decision": "Send to Finance Team",
                "message": "Employee grade not available; manual review required",
                "metrics": None,
                "rule_band": "no_policy"
            }
            return JSONResponse(content=jsonable_encoder({
                "tag": result["tag"],
                "decision": result["decision"],
                "comments": result["message"],
                "validation": result
            }), status_code=200)

        policies_df = _db_utils.load_policies_df(emp_grade)
        policies_list = policies_df.to_dict("records")
        policy_row = _agent._pick_policy_for(employee_details_list, policies_list, payload_dict.get("category"))

        validator = _agent.ValidationAgent(use_llm_message=True)
        result = validator.validate(employee_row, policy_row, payload_dict)

        return JSONResponse(content=jsonable_encoder({
            "tag": result.get("tag"),
            "decision": result.get("decision"),
            "comments": result.get("message"),
            "validation": result
        }), status_code=200)

    # --------- EXTRACT ONLY ---------
    if phase == "extract":
        img = pick("image_name")
        eid = pick("emp_id")
        outdir = pick("json_out_dir", "./output/langchain_json")
        save = bool(pick("save_json_file", True))

        if not img:
            raise HTTPException(status_code=400, detail="image_name is required for phase=extract")

        if eid:
            LAST_EMP_ID = eid

        state = {
            "file_path": img,
            "employee_id_hint": eid,
            "json_out_dir": outdir,
            "save_json_file": save,
        }

        state = _agent.extract_node(state)
        extraction = state.get("extraction")
        if not extraction:
            raise HTTPException(status_code=500, detail="Extraction failed")

        payload_json = _agent.payload_to_json_ready(extraction["payload"])

        return JSONResponse(
            content=jsonable_encoder({
                "process_id": state.get("process_id"),
                "extraction": {
                    "payload": payload_json,
                    "ocr_engine": extraction.get("ocr_engine"),
                    "raw_text_preview": extraction.get("raw_text_preview"),
                }
            }),
            status_code=200
        )

    # --------- FULL PIPELINE (extract + validate) ---------
    if phase == "full":
        img = pick("image_name")
        eid = pick("emp_id")
        outdir = pick("json_out_dir", "./output/langchain_json")
        save = bool(pick("save_json_file", True))

        if not img:
            raise HTTPException(status_code=400, detail="image_name is required for phase=full")

        if eid:
            LAST_EMP_ID = eid

        state = {
            "file_path": img,
            "employee_id_hint": eid,
            "json_out_dir": outdir,
            "save_json_file": save
        }

        state = _agent.extract_node(state)
        state = _agent.validate_node(state)

        extraction = state.get("extraction") or {}
        payload_json = _agent.payload_to_json_ready(extraction.get("payload", {}))
        validation = state.get("validation") or {}

        return JSONResponse(
            content=jsonable_encoder({
                "process_id": state.get("process_id"),
                "extraction": {
                    "payload": payload_json,
                    "ocr_engine": extraction.get("ocr_engine"),
                    "raw_text_preview": extraction.get("raw_text_preview"),
                },
                "validation": validation,
                "tag": state.get("tag"),
                "decision": state.get("decision"),
                "comments": (validation.get("message") if isinstance(validation, dict) else None),
            }),
            status_code=200
        )

    # otherwise invalid phase
    raise HTTPException(status_code=400, detail="phase must be one of: extract | validate | full")


# ============================================================
# ======  ANALYTICS / KPI ROUTES (moved from queries.py) =====
# ============================================================

@app.get("/meta/health")
def health():
    return {"db_tables": _db_utils.get_table_health()}

@app.get("/claims/summary")
def claims_summary():
    summary = _db_utils.get_claims_summary()
    proc = _db_utils.get_avg_processing_time_by_date()
    summary.update(proc)

    total = summary.get("total_claims", 0) or 0
    auto = summary.get("auto_approved", 0) or 0
    summary["automation_rate"] = round((auto / total) if total else 0, 4)
    return summary

@app.get("/claims/by-date")
def claims_by_date(start_date: str | None = None, end_date: str | None = None):
    return _db_utils.get_claims_by_date(start_date, end_date)

@app.get("/claims/automation-rate")
def automation_rate(start_date: str | None = None, end_date: str | None = None):
    return _db_utils.get_automation_rate_by_date(start_date, end_date)

@app.get("/claims/processing-time/by-date")
def processing_time_by_date(start_date: str | None = None, end_date: str | None = None):
    return _db_utils.get_processing_time_by_date(start_date, end_date)

@app.get("/claims/by-department")
def by_department(limit: int = 20):
    return _db_utils.get_claims_by_department(limit)

@app.get("/claims/top-employees")
def top_employees(limit: int = 20):
    return _db_utils.get_top_employees(limit)

@app.get("/claims/duplicates")
def duplicates(threshold: int = 2):
    return _db_utils.get_duplicates(threshold)

@app.get("/claims/amount-distribution")
def amount_distribution():
    return _db_utils.get_amount_distribution(buckets=[0, 100, 500, 1000, 5000, 10000])

@app.get("/claims/pending/aging")
def pending_aging():
    return _db_utils.get_pending_aging()

@app.get("/claims/details/{claim_id}")
def claim_details(claim_id: str):
    data = _db_utils.get_claim_details(claim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Claim not found")
    return data


# ======================================================
# ======  CLAIM WORKFLOW / CRUD ROUTES (db_utils)  =====
# ======================================================

class ClaimCreateBody(BaseModel):
    payload_out: Dict[str, Any]
    status: Any  # can be string or validator dict

class ValidationLogBody(BaseModel):
    employee_id: str
    validation_obj: Dict[str, Any]

class UpdateStatusBody(BaseModel):
    status_val: str
    auto_approved: bool = False

class ManagerDecisionBody(BaseModel):
    decision: str  # "Approve" | "Reject"
    comment: str = ""
    approver_id: Optional[str] = None

class FinanceDecisionBody(BaseModel):
    decision: str  # "Approve" | "Reject"
    comment: str = ""
    approver_id: Optional[str] = None

@app.get("/api/policies")
def api_get_policies():
    return _db_utils.get_expense_policy()

@app.get("/api/per-diem")
def api_get_per_diem(emp_id: Optional[str] = Query(default=None)):
    return _db_utils.get_per_diem_rates(emp_id)

@app.get("/api/employees/{emp_id}")
def api_get_employee(emp_id: str):
    recs = _db_utils.get_employee_details(emp_id)
    if not recs:
        raise HTTPException(status_code=404, detail=f"No employee found for id '{emp_id}'")
    return recs[0]

@app.get("/api/claims/recent")
def api_recent_claims(emp_id: str = Query(...), limit: int = Query(50, ge=1, le=500)):
    df = _db_utils.load_recent_claims(emp_id, limit)
    try:
        return df.to_dict(orient="records")
    except Exception:
        return df

@app.get("/api/claims/manager/pending")
def api_manager_pending(manager_email: Optional[str] = None, manager_id: Optional[str] = None):
    df = _db_utils.load_manager_team_pending_claims(manager_email, manager_id)
    try:
        return df.to_dict(orient="records")
    except Exception:
        return df

@app.get("/api/claims/finance/pending")
def api_finance_pending():
    df = _db_utils.load_finance_pending_claims()
    try:
        return df.to_dict(orient="records")
    except Exception:
        return df

@app.get("/api/claims/new-id")
def api_generate_claim_id():
    return {"claim_id": _db_utils.generate_claim_id()}

@app.post("/api/claims")
def api_create_claim(body: ClaimCreateBody):
    claim_id = _db_utils.save_expense_claim(body.payload_out, body.status)
    return {"claim_id": claim_id}

@app.post("/api/claims/{claim_id}/validation-log")
def api_log_validation(claim_id: str, body: ValidationLogBody):
    wrote = _db_utils.log_validation_result(claim_id, body.employee_id, body.validation_obj)
    return wrote

@app.patch("/api/claims/{claim_id}/status")
def api_update_claim_status(claim_id: str, body: UpdateStatusBody):
    _db_utils.update_claim_status(claim_id, body.status_val, body.auto_approved)
    return {"ok": True, "claim_id": claim_id, "status": body.status_val, "auto_approved": body.auto_approved}

@app.post("/api/claims/{claim_id}/manager-decision")
def api_manager_decision(claim_id: str, body: ManagerDecisionBody):
    _db_utils.manager_update_claim_decision(
        claim_id, body.decision, body.comment, body.approver_id or ""
    )
    return {"ok": True, "claim_id": claim_id, "status": "Approved" if body.decision == "Approve" else "Rejected"}

@app.post("/api/claims/{claim_id}/finance-decision")
def api_finance_decision(claim_id: str, body: FinanceDecisionBody):
    _db_utils.finance_update_claim_decision(
        claim_id, body.decision, body.comment, body.approver_id or ""
    )
    return {"ok": True, "claim_id": claim_id, "status": "Approved" if body.decision == "Approve" else "Rejected"}


# ======================================================
# ======  EMAIL UTIL ROUTES  ==========================
# ======================================================

class SendEmailBody(BaseModel):
    recipient_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Plain text email body")
    from_name: Optional[str] = Field(None, description="Override From display name (optional)")

class EmployeeAckDraftBody(BaseModel):
    claim_id: str
    employee_name: Optional[str] = None
    employee_id: str
    category: str
    amount: Any
    currency: str
    vendor: Optional[str] = None
    expense_date: Optional[str] = None
    tag: str
    decision: Optional[str] = None
    comments: Optional[str] = None

class EmployeeUpdateDraftBody(BaseModel):
    claim_id: str
    employee_name: Optional[str] = None
    employee_id: str
    actor_role: str
    decision: str
    comment: Optional[str] = None

@app.post("/api/utils/email/send")
def api_utils_send_email(body: SendEmailBody):
    ok = mail_utils.send_email(
        recipient_email=body.recipient_email,
        subject=body.subject,
        body=body.body,
        from_name=body.from_name
    )
    if not ok:
        return {
            "ok": False,
            "message": "Email send failed. Check SMTP credentials/logs.",
            "to": body.recipient_email
        }
    return {"ok": True, "to": body.recipient_email, "subject": body.subject}

@app.post("/api/utils/draft/employee-ack")
def api_utils_draft_employee_ack(body: EmployeeAckDraftBody):
    subject, content = mail_utils.draft_employee_ack_on_upload(
        claim_id=body.claim_id,
        employee_name=body.employee_name,
        employee_id=body.employee_id,
        category=body.category,
        amount=body.amount,
        currency=body.currency,
        vendor=body.vendor,
        expense_date=body.expense_date,
        tag=body.tag,
        decision=body.decision,
        comments=body.comments,
    )
    return {"subject": subject, "body": content}

@app.post("/api/utils/draft/employee-update")
def api_utils_draft_employee_update(body: EmployeeUpdateDraftBody):
    subject, content = mail_utils.draft_employee_update_on_action(
        claim_id=body.claim_id,
        employee_name=body.employee_name,
        employee_id=body.employee_id,
        actor_role=body.actor_role,
        decision=body.decision,
        comment=body.comment,
    )
    return {"subject": subject, "body": content}