# app.py

from fastapi import FastAPI, HTTPException, Query, Request, Header, Depends
import image_extraction as ie
import schema as _schema
import services as _services
from sqlalchemy import orm as _orm
import fastapi as _fastapi
import db_utils as _db_utils
from typing import List, TYPE_CHECKING
from fastapi.responses import JSONResponse
from starlette import status
from pathlib import Path
import agent as _agent
import os

from fastapi.encoders import jsonable_encoder

app = _fastapi.FastAPI()

LAST_EMP_ID: str | None = None
EMP_DETAILS = []

# Where to save JSON outputs
OUT_DIR = Path(os.environ.get("OUT_DIR", "./output/langchain_json"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Basic extraction endpoints
# -----------------------------
@app.post("/extract_image_data", response_class=JSONResponse, status_code=status.HTTP_200_OK)
def get_image_data(
    image_name: str = Query(..., description="Name of the image file"),
    emp_id: str = Query(..., description="Enter Employee ID"),
):
    """
    Simple passthrough to image_extraction module, stores output json for the given image.
    Also sets LAST_EMP_ID to allow subsequent calls that need the context.
    """
    global LAST_EMP_ID
    try:
        LAST_EMP_ID = emp_id
        img_json = ie.extract_json_from_image(image_name, emp_id)
        ie.save_json(img_json, OUT_DIR, image_name)
        return {"image_name": image_name, "data": img_json}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/extract_pdf_data", response_class=JSONResponse, status_code=status.HTTP_200_OK)
def get_pdf_data(
    pdf_name: str = Query(..., description="Name of the PDF file"),
    emp_id: str = Query(..., description="Enter Employee ID"),
):
    """
    Simple passthrough to image_extraction module for PDFs, stores output json.
    Also sets LAST_EMP_ID to allow subsequent calls that need the context.
    """
    global LAST_EMP_ID
    try:
        LAST_EMP_ID = emp_id
        # Your ie module has extract_json_from_pdf_text; keep it as-is.
        pdf_json = ie.extract_json_from_pdf_text(pdf_name)
        ie.save_json(pdf_json, OUT_DIR, pdf_name)
        return {"pdf_name": pdf_name, "data": pdf_json}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Example: any other API can reuse emp_id without new params ---
@app.get("/whoami")
def whoami():
    """Return the last emp_id received"""
    if not LAST_EMP_ID:
        raise HTTPException(status_code=404, detail="No emp_id found. Call a route that sets it first.")
    return {"emp_id": LAST_EMP_ID}


@app.get("/api/employee_details")
def get_employee_details():
    """
    Returns employee details for the LAST_EMP_ID captured earlier.
    Use one of the extraction endpoints (or /api/Agent with emp_id) before calling this.
    """
    global EMP_DETAILS

    if not LAST_EMP_ID:
        raise HTTPException(status_code=404, detail="No emp_id found. Call a route that sets it first.")
    EMP_DETAILS = _db_utils.get_employee_details(LAST_EMP_ID)

    if not EMP_DETAILS:
        raise HTTPException(status_code=404, detail=f"No employee found for id '{LAST_EMP_ID}'")

    print("Fetched EMP_DETAILS from DB:", EMP_DETAILS)
    return EMP_DETAILS


# -----------------------------
# DB-backed claim creation demo
# -----------------------------
@app.post("/api/InvoiceData", response_model=_schema.ExpenseClaims)
async def create_expense_claims(
    expense_claims: _schema.createExpenseClaims,
    db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    return await _services.create_expense_claims(expense_claims=expense_claims, db=db)


# -----------------------------
# Legacy extractor-only entry
# -----------------------------
@app.post("/api/ExtractorAgent")
async def extractor_agent(
    image_name: str = Query(..., description="Name of the image file"),
    emp_id: str = Query(..., description="Enter Employee ID"),
    json_out_dir: str = Query(..., description="Directory to save JSON output"),
    save_json_file: bool = Query(..., description="Flag to save JSON file"),
):
    """
    Runs extraction only using agent.extract_node and returns the internal state.
    """
    state = {
        "file_path": image_name,
        "employee_id_hint": emp_id,
        "json_out_dir": json_out_dir,
        "save_json_file": save_json_file,
    }
    final_state = _agent.extract_node(state)
    return final_state


# -----------------------------
# Unified Agent endpoint
# -----------------------------
@app.post("/api/Agent", response_class=JSONResponse, status_code=status.HTTP_200_OK)
async def agent_router(
    request: Request,
    image_name: str | None = Query(default=None, description="Path to file on server (image/pdf)"),
    emp_id: str | None = Query(default=None, description="Employee ID"),
    json_out_dir: str = Query(default="./output/langchain_json", description="Directory to save JSON"),
    save_json_file: bool = Query(default=True, description="Save extracted JSON file"),
    phase: str = Query(default="extract", description="extract | validate | full"),
):
    """
    Unified Agent endpoint:
      - phase=extract  : run extraction only, return normalized payload for UI
      - phase=validate : expects edited JSON payload in body; runs policy validation only (returns comments)
      - phase=full     : extract + validate in one shot (returns comments)
    """
    global LAST_EMP_ID

    phase = (phase or "extract").lower()

    # Read JSON body once (if present)
    body: dict | None = None
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = None
    except Exception:
        body = None

    # capture LAST_EMP_ID if provided
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
        val = query_map.get(field_name, None)
        if val is not None:
            return val
        if body and (field_name in body) and (body[field_name] is not None):
            return body[field_name]
        for fb in fallbacks:
            if fb is not None:
                return fb
        return None

    # -------------------------
    # VALIDATE ONLY (human-in-loop)
    # -------------------------
    if phase == "validate":
        if not body:
            raise HTTPException(status_code=400, detail="Expected JSON body for phase=validate")

        # Normalize incoming payload via Pydantic (dates/amounts/items)
        try:
            inv = _agent.InvoicePayload(**body)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

        if not inv.employee_id:
            raise HTTPException(status_code=400, detail="employee_id is required in the payload")

        payload_dict = inv.model_dump(mode="python")

        # Load employee row from your DB utils
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
                "comments": result["message"],   # <- UI-friendly comment
                "validation": result
            }), status_code=200)

        # Resolve policies for this grade and pick one for the category
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
                "comments": result["message"],   # <- UI-friendly comment
                "validation": result
            }), status_code=200)

        policies_df = _agent.load_policies_df(emp_grade)
        policies_list = policies_df.to_dict("records")
        policy_row = _agent._pick_policy_for(employee_details_list, policies_list, payload_dict.get("category"))

        # Run validator (deterministic + optional LLM message)
        validator = _agent.ValidationAgent(use_llm_message=True)
        result = validator.validate(employee_row, policy_row, payload_dict)

        return JSONResponse(content=jsonable_encoder({
            "tag": result.get("tag"),
            "decision": result.get("decision"),
            "comments": result.get("message"),   # <- UI-friendly comment
            "validation": result
        }), status_code=200)

    # -------------------------
    # EXTRACT ONLY (for UI form)
    # -------------------------
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

        # Extract node only (no validation yet) -> returns dict in state['extraction']
        state = _agent.extract_node(state)
        extraction = state.get("extraction")
        if not extraction:
            raise HTTPException(status_code=500, detail="Extraction failed")

        # Ensure JSON-safe payload (dates → ISO) from the dict
        payload_json = _agent.payload_to_json_ready(extraction["payload"])

        return JSONResponse(
            content=jsonable_encoder({
                "process_id": state.get("process_id"),
                "extraction": {
                    "payload": payload_json,
                    "ocr_engine": extraction.get("ocr_engine"),
                    "raw_text_preview": extraction.get("raw_text_preview")
                }
            }),
            status_code=200
        )

    # -------------------------
    # FULL (extract + validate)
    # -------------------------
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

        # Run pipeline explicitly (no graph.invoke)
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
                # Provide the human-friendly rationale right on the top-level for UI
                "comments": (validation.get("message") if isinstance(validation, dict) else None),
            }),
            status_code=200
        )

    # Unknown phase
    raise HTTPException(status_code=400, detail="phase must be one of: extract | validate | full")
