from fastapi import FastAPI ,  HTTPException, Query, Request, Header , Depends
import image_extraction as ie
import schema as _schema
import services as _services
from  sqlalchemy import orm as _orm
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

@app.post("/extract_image_data", response_class=JSONResponse, status_code=status.HTTP_200_OK)
def get_image_data(
    image_name: str = Query(..., description="Name of the image file"),
    emp_id: str = Query(..., description="Enter Employee ID"),  # ensures emp_id is present + set on request.state
):
    global LAST_EMP_ID
    try:
        LAST_EMP_ID = emp_id

        img_json = ie.extract_json_from_image(image_name, emp_id)
        ie.save_json(img_json, OUT_DIR, image_name)
        return {"image_name": image_name,  "data": img_json}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/extract_pdf_data", response_class=JSONResponse, status_code=status.HTTP_200_OK)
def get_pdf_data(
    pdf_name: str = Query(..., description="Name of the PDF file"),
    emp_id: str = Query(..., description="Enter Employee ID"),  # ensures emp_id is present + set on request.state
):
    global LAST_EMP_ID
    try:
        LAST_EMP_ID = emp_id

        pdf_json = ie.extract_json_from_pdf_text(pdf_name)
        ie.save_json(pdf_json, OUT_DIR, pdf_name)
        return {"pdf_name": pdf_name,  "data": pdf_json}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Example: any other API can reuse emp_id without new params ---
@app.get("/whoami")
def whoami():
    """Return the last emp_id received in /test"""
    if not LAST_EMP_ID:
        raise HTTPException(status_code=404, detail="No emp_id found. Call /test first.")
    return {"emp_id": LAST_EMP_ID}

@app.get("/api/employee_details")
def get_employee_details():
    global EMP_DETAILS

    # check if emp_id is set
    if not LAST_EMP_ID:
        raise HTTPException(status_code=404, detail="No emp_id found. Call /test first.")
    EMP_DETAILS =  _db_utils.get_employee_details(LAST_EMP_ID)

    if not EMP_DETAILS:
        raise HTTPException(status_code=404, detail=f"No employee found for id '{LAST_EMP_ID}'")

    # append to the global list
    print("Fetched EMP_DETAIL'S from DB:", EMP_DETAILS)
    return  EMP_DETAILS


@app.post("/api/InvoiceData", response_model=_schema.ExpenseClaims)
async def create_expense_claims(
    expense_claims: _schema.createExpenseClaims,
    db: _orm.Session = _fastapi.Depends(_services.get_db)
):
    return await _services.create_expense_claims(expense_claims=expense_claims, db=db) 


@app.post("/api/ExtractorAgent")
async def extractor_agent(
    image_name: str = Query(..., description="Name of the image file"),
    emp_id: str = Query(..., description="Enter Employee ID"),
    json_out_dir: str = Query(..., description="Directory to save JSON output"),
    save_json_file: bool = Query(..., description="Flag to save JSON file"),
):
    state = {"file_path": image_name , 
        "employee_id_hint": emp_id,
        "json_out_dir": json_out_dir,
        "save_json_file": save_json_file
        }

    final_state  = _agent.extract_node(state)
    return final_state



@app.post("/api/Agent", response_class=JSONResponse, status_code=status.HTTP_200_OK)
async def agent_router(
    request: Request,
    # Query fallbacks (body is also supported; see pick() below)
    image_name: str | None = Query(default=None, description="Path to file on server (image/pdf)"),
    emp_id: str | None = Query(default=None, description="Employee ID"),
    json_out_dir: str = Query(default="./output/langchain_json", description="Directory to save JSON"),
    save_json_file: bool = Query(default=True, description="Save extracted JSON file"),
    phase: str = Query(default="extract", description="extract | validate | full"),
):
    """
    Unified Agent endpoint:
      - phase=extract  : run extraction only, return normalized payload for UI
      - phase=validate : expects edited JSON payload in body; runs policy validation only
      - phase=full     : extract + validate in one shot (minimal summary)
    """
    phase = (phase or "extract").lower()

    # Read JSON body once (if present)
    body: dict | None = None
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = None
    except Exception:
        body = None

    # Capture query args in a map so inner pick() can read them
    query_map = {
        "image_name": image_name,
        "emp_id": emp_id,
        "json_out_dir": json_out_dir,
        "save_json_file": save_json_file,
        "phase": phase,
    }

    # Resolver: prefer query param, then body field, then provided fallbacks
    def pick(field_name: str, *fallbacks):
        # 1) value from query map
        val = query_map.get(field_name, None)
        if val is not None:
            return val
        # 2) value from JSON body
        if body and (field_name in body) and (body[field_name] is not None):
            return body[field_name]
        # 3) fallbacks
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

        # Coerce to canonical schema (handles dates/totals/items/category normalization)
        try:
            inv = _agent.InvoicePayload(**body)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

        if not inv.employee_id:
            raise HTTPException(status_code=400, detail="employee_id is required in the payload")

        # Load employee row
        employees_df = _agent.load_employees_df(inv.employee_id)
        if employees_df.empty:
            return JSONResponse(
                content=jsonable_encoder({
                    "Final tag": "Reject",
                    "Decision": "Reject",
                    "Findings": [{
                        "severity": "HARD",
                        "rule_id": "EMP-404",
                        "message": f"Employee '{inv.employee_id}' not found"
                    }]
                }),
                status_code=200
            )

        # Resolve grade → fetch policies
        emp_grade = employees_df["grade"].iloc[0] if "grade" in employees_df.columns else None
        if not emp_grade:
            return JSONResponse(
                content=jsonable_encoder({
                    "Final tag": "Send for validation",
                    "Decision": "Send for validation",
                    "Findings": [{
                        "severity": "SOFT",
                        "rule_id": "EMP-000",
                        "message": "Employee grade not available; manual review required"
                    }]
                }),
                status_code=200
            )

        policies_df = _agent.load_policies_df(emp_grade)

        # Run validation
        validator = _agent.ValidationAgent(employees_df, policies_df)
        result = validator.validate(inv)

        findings_list = [{
            "severity": f.severity,
            "rule_id": f.rule_id,
            "message": f.message
        } for f in (result.findings or [])]

        return JSONResponse(
            content=jsonable_encoder({
                "Final tag": result.decision.value,
                "Decision": result.decision.value,
                "Findings": findings_list
            }),
            status_code=200
        )

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

        state = {
            "file_path": img,
            "employee_id_hint": eid,
            "json_out_dir": outdir,
            "save_json_file": save,
        }
        # Extract node only (no validation yet)
        state = _agent.extract_node(state)
        extraction = state.get("extraction")
        if not extraction:
            raise HTTPException(status_code=500, detail="Extraction failed")

        # Ensure JSON-safe payload (dates → ISO)
        payload_dict = extraction.payload.model_dump(mode="json")

        return JSONResponse(
            content=jsonable_encoder({
                "extraction": {
                    "payload": payload_dict,
                    "ocr_engine": extraction.ocr_engine,
                    "raw_text_preview": extraction.raw_text_preview
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

        state = {
            "file_path": img,
            "employee_id_hint": eid,
            "json_out_dir": outdir,
            "save_json_file": save
        }
        final_state = _agent.graph.invoke(state)

        validation = final_state.get("validation")
        if not validation:
            return JSONResponse(
                content=jsonable_encoder({
                    "Final tag": final_state.get("tag"),
                    "Decision": None,
                    "Findings": [],
                    "error": "Validation stage failed or missing"
                }),
                status_code=500
            )

        findings_list = [{
            "severity": f.severity,
            "rule_id": f.rule_id,
            "message": f.message
        } for f in (validation.findings or [])]

        return JSONResponse(
            content=jsonable_encoder({
                "Final tag": final_state.get("tag"),
                "Decision": validation.decision.value if validation.decision else None,
                "Findings": findings_list
            }),
            status_code=200
        )

    # Unknown phase
    raise HTTPException(status_code=400, detail="phase must be one of: extract | validate | full")