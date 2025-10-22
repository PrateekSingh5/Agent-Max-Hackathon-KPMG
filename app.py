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

@app.post("/api/Agent", response_model=List[_schema.ExpenseClaims])
async def agent_state(
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
    

    

    final_state  = _agent.graph.invoke(state)

    # --- Extract fields for response ---
    validation = final_state.get("validation")

    # Guard for missing validation results
    if not validation:
        return JSONResponse(
            content={
                "Final tag": final_state.get("tag"),
                "Decision": None,
                "Findings": [],
                "error": "Validation stage failed or missing"
            },
            status_code=500
        )

    findings_list = []
    if getattr(validation, "findings", None):
        for f in validation.findings:
            findings_list.append({
                "severity": f.severity,
                "rule_id": f.rule_id,
                "message": f.message
            })

    # --- Return minimal structured response ---
    return JSONResponse(
        content={
            "Final tag": final_state.get("tag"),
            "Decision": validation.decision.value if validation.decision else None,
            "Findings": findings_list
        }
    )


    