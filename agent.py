import os
import io
import uuid
import json
import enum
import datetime as dt
from typing import List, Optional, Dict, Any, Literal, TypedDict
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field, validator , field_validator, model_validator
from sqlalchemy import create_engine, text
# --- LangGraph ---
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# =========================
# ENV & DB
# =========================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:rootpassword@localhost:5432/agent_max")
engine = create_engine(DATABASE_URL, future=True)



## PDF and Image Extraction Imports

# pip install -q langchain langchain-openai pillow python-dotenv

import os, json, glob, base64
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import fitz
 
# --- Setup ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
# Vision model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,api_key= OPENAI_API_KEY ).bind(
    # Force valid JSON output (OpenAI "JSON mode")
    response_format={"type": "json_object"}
)

# -------------------------------- For Image -----------------------------
def image_to_data_url(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

INSTRUCTIONS_IMAGE = (
    "You are an expert at visually parsing documents (invoices, receipts, forms, IDs, etc.). "
    "Look at the image and return a SINGLE JSON object that captures the content you see. "
    "Infer keys from the document itself (e.g., 'invoice_number', 'date', 'seller', 'buyer', "
    "'items', 'totals', 'tax', 'address', etc.)—only if they appear. "
    "If there are tables, represent them as arrays of row objects. "
    "If you see line items, include them as an array with fields derived from the column headers. "
    "Prefer numbers for numeric values. Use ISO date strings if clear. "
    "Do NOT add commentary. Do NOT wrap in markdown—return only JSON."
    "- If a field is missing, simply omit it (do not invent data)."
    "- Include important fields you can infer from text (seller, address, contact, invoice_no/date/due, line_items_summary, amounts, instructions).\n"
    "- Deduplicate and correct minor OCR spacing like 'HonkKong' -> 'Hong Kong', 'DueDate:' -> 'due date'."
    "- If bill is for travel get from and too locations." 
    "- If bill is for hotel get hotel name, location, check in check out and from and till."
    "- Tag currancy if possible (e.g., USD, EUR, GBP, INR)."
)

def extract_json_from_image(image_path: str, emp_id) -> dict:
    msg = HumanMessage(
        content=[
            {"type": "text", "text": INSTRUCTIONS_IMAGE},
            {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
        ]
    )
    resp = llm.invoke([msg])
    text = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    try:
        text["Emploee ID"] = emp_id
        return json.loads(text)
    except Exception:
        # Fallback: try to salvage JSON between first { and last }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
        raise ValueError(f"Model did not return valid JSON:\n{text}")

def save_json(data, out_dir,image_name):
    out_dir = Path(out_dir)
    out_path = out_dir / (Path(image_name).stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {Path(out_path).name} -> {out_path}")


# ---------------------------------------For PDF -----------------------------


# --- Instructions ---
INSTRUCTIONS_PDF = (
    "You are an expert at parsing invoice or receipt text. "
    "I will give you the raw text extracted from a PDF document. "
    "Return a SINGLE JSON object with fields that appear (e.g., 'invoice_number', 'date', 'seller', 'buyer', 'items', 'total', 'tax', etc.). "
    "Represent line items or tables as arrays of row objects. "
    "Prefer numbers for numeric values, ISO date format for dates, and omit missing fields. "
    "If it's a travel bill, extract 'from' and 'to' locations; if it's a hotel bill, extract 'hotel_name', "
    "'location', 'check_in', and 'check_out'. Tag currency like INR, USD, etc. "
    "Return only valid JSON, no explanations."
    "- If bill is for travel get from and too locations." 
    "- If bill is for hotel get hotel name, location, check in check out and from and till."
    "- Tag currancy if possible (e.g., USD, EUR, GBP, INR)."
    "-Tag categoty of bill (e.g., travel, hotel, food, office supplies, others)."
)

# --- Helper: read text from local PDF ---
def read_pdf_text(pdf_path: str) -> str:
    """Extract all text from a local PDF file."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text.strip()

# --- Main Function ---
def extract_json_from_pdf_text(pdf_path: str, emp_id) -> dict:
    """Extract structured JSON directly from a local PDF (no image rendering)."""
    pdf_text = read_pdf_text(pdf_path)

    msg = HumanMessage(
        content=[
            {"type": "text", "text": f"{INSTRUCTIONS_PDF}\n\nDocument Text:\n{pdf_text}"}
        ]
    )

    resp = llm.invoke([msg])
    text = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    try:
        return json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
        raise ValueError(f"Invalid JSON returned:\n{text}")


################

# =========================
# DOMAIN MODELS
# =========================

class Decision(str, enum.Enum):
    APPROVED = "Approved"
    REJECT = "Reject"
    SEND_FOR_VALIDATION = "Send for validation"

class InvoiceItem(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    city: Optional[str] = None


class Seller(BaseModel):
    hotel_name: Optional[str] = None
    location: Optional[str] = None


class Buyer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class BookingDetails(BaseModel):
    booking_number: Optional[str] = None
    payment_reference: Optional[str] = None
    check_in: Optional[dt.date] = None
    check_out: Optional[dt.date] = None


class InvoicePayload(BaseModel):
    # canonical fields used elsewhere in your pipeline (now optional)
    invoice_id: Optional[str] = Field(default_factory=lambda: f"INV-{uuid.uuid4().hex[:8].upper()}")
    employee_id: Optional[str] = None
    expense_date: Optional[dt.date] = None
    vendor: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    items: List[InvoiceItem] = Field(default_factory=list)

    # keep raw fields (optional) so you can store the original structure too
    invoice_number: Optional[str] = None
    date: Optional[dt.date] = None
    seller: Optional[Seller] = None
    buyer: Optional[Buyer] = None
    booking_details: Optional[BookingDetails] = None
    total: Optional[float] = None
    category: Optional[str] = None

    model_config = {"populate_by_name": True}

    # Map incoming JSON -> canonical fields (runs before validation)
    @model_validator(mode="before")
    def _map_raw_to_canonical(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return v
        out = dict(v)

        # invoice_id from invoice_number if present
        out.setdefault("invoice_id", v.get("invoice_number"))

        # employee_id from "Employee ID"
        out.setdefault("employee_id", v.get("Employee ID"))

        # expense_date from date
        out.setdefault("expense_date", v.get("date"))

        # total_amount from total
        out.setdefault("total_amount", v.get("total"))

        # vendor from seller.hotel_name (or seller.name)
        if "vendor" not in out:
            seller = v.get("seller")
            if isinstance(seller, dict):
                out["vendor"] = seller.get("hotel_name") or seller.get("name")

        # currency default if missing/empty
        if not out.get("currency"):
            out["currency"] = "INR"

        # ensure items key exists (empty list if none)
        out.setdefault("items", [])
        return out

    @field_validator("expense_date", mode="before")
    def _parse_date(cls, val):
        if isinstance(val, dt.date) or val is None:
            return val
        s = str(val)[:10]
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except Exception:
                pass
        try:
            return dt.date.fromisoformat(s)
        except Exception:
            return None

    @field_validator("total_amount")
    def _non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("total_amount cannot be negative")
        return v

    @field_validator("date", "expense_date", mode="before")
    def _coerce_datetime_to_date(cls, v):
        """
        Converts ISO datetime strings (with time) to date-only.
        e.g. '2025-09-04T10:19:00' -> datetime.date(2025, 9, 4)
        """
        if v is None:
            return v
        if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
            return v
        try:
            if isinstance(v, str):
                # Strip time if present
                v = v.split("T")[0]
            return dt.date.fromisoformat(str(v))
        except Exception:
            try:
                # As fallback, parse using datetime
                return dt.datetime.fromisoformat(str(v)).date()
            except Exception:
                return None
            
    @field_validator("seller", mode="before")
    def _coerce_seller(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        # If seller is a plain string like "Uber" → map to Seller(hotel_name=<string>) or name
        if isinstance(v, str):
            return {"hotel_name": v}  # or {"name": v}
        return None  # fallback to None if unknown shape

    @field_validator("buyer", mode="before")
    def _coerce_buyer(cls, v):
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, str):
            return {"name": v}
        return None

        

class ValidationFinding(BaseModel):
    rule_id: str
    severity: Literal["HARD", "SOFT"]
    message: str
    context: Dict[str, Any] = {}

class ValidationResult(BaseModel):
    decision: Decision
    findings: List[ValidationFinding]
    policy_rows_applied: List[Dict[str, Any]] = []
    employee_row: Optional[Dict[str, Any]] = None
    computed: Dict[str, Any] = {}

class ExtractionResult(BaseModel):
    payload: InvoicePayload
    raw_text_preview: Optional[str] = None
    ocr_engine: Optional[str] = None

class ProcessResponse(BaseModel):
    process_id: str
    extraction: ExtractionResult
    validation: ValidationResult



# =========================
# DATA ACCESS
# =========================
def load_employees_df(emp_id : str) -> pd.DataFrame:
    query = text("SELECT * FROM employees WHERE employee_id = :emp_id;")

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"emp_id": emp_id})

def load_policies_df(grade: str) -> pd.DataFrame:

    query = text("SELECT * FROM expense_policies WHERE applicable_grades ILIKE :pattern")

    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"pattern": f"%{grade}%"})

def comma_list(cell: Optional[str]) -> List[str]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    return [x.strip() for x in str(cell).split(",") if x.strip()]

def sum_items(items: List[InvoiceItem]) -> float:
    return round(sum(i.amount for i in items), 2)




import os, json, glob, re, datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional

SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".tiff"}

# --------- Normalization utilities (map raw JSON -> consistent payload) ---------

def _to_float(x) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0

def _parse_date_any(s: str) -> Optional[dt.date]:
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    # try ISO-like fallback
    try:
        return dt.date.fromisoformat(s[:10])
    except Exception:
        return None

def _safe_total(j: Dict[str, Any]) -> float:
    for k in ["total", "grand_total", "amount_due", "total_amount", "net_total", "invoice_total"]:
        if k in j:
            val = _to_float(j[k])
            if val > 0:
                return val
    # fallback from items if possible
    items = _safe_items(j)
    return round(sum(it["amount"] for it in items), 2) if items else 0.0

def _safe_date(j: Dict[str, Any]) -> dt.date:
    for k in ["invoice_date", "date", "bill_date", "issue_date", "created_on", "dated"]:
        if k in j and j[k]:
            d = _parse_date_any(j[k])
            if d:
                return d
    return dt.date.today()

def _safe_vendor(j: Dict[str, Any]) -> Optional[str]:
    for k in ["seller", "vendor", "merchant", "company", "hotel_name", "restaurant_name", "airline"]:
        if j.get(k):
            return str(j[k])
    # try nested dictionaries (common in LLM outputs)
    for k in ["seller", "vendor", "merchant", "company"]:
        v = j.get(k)
        if isinstance(v, dict):
            # pick a plausible name-like field
            for kk in ["name", "legal_name", "display_name"]:
                if v.get(kk):
                    return str(v[kk])
    return None

def _safe_currency(j: Dict[str, Any]) -> str:
    return str(j.get("currency", "INR")).upper()

def _safe_items(j: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = None
    for k in ["items", "line_items", "rows", "table", "charges"]:
        v = j.get(k)
        if isinstance(v, list) and v:
            candidates = v
            break
    out: List[Dict[str, Any]] = []
    if candidates:
        for row in candidates:
            if not isinstance(row, dict):
                continue
            desc = row.get("description") or row.get("item") or row.get("service") or "Item"
            cat  = row.get("category") or j.get("category") or "Uncategorized"
            amt  = row.get("amount") or row.get("price") or row.get("total") or 0
            cur  = (row.get("currency") or j.get("currency") or "INR")
            merch = row.get("merchant") or j.get("seller") or j.get("vendor")
            city = row.get("city") or j.get("city")
            out.append({
                "description": str(desc),
                "category": str(cat),
                "amount": _to_float(amt),
                "currency": str(cur).upper(),
                "merchant": merch if merch else None,
                "city": city if city else None
            })
    # If nothing found, return a single "Total" line using the overall total
    if not out:
        out.append({
            "description": "Total",
            "category": str(j.get("category", "Uncategorized")),
            "amount": _safe_total(j),
            "currency": _safe_currency(j),
            "merchant": j.get("seller") or j.get("vendor"),
            "city": j.get("city")
        })
    return out

def _normalize_payload(raw_json: Dict[str, Any], fallback_emp_id: Optional[str]) -> Dict[str, Any]:
    """
    Returns a consistent structure:
    {
      "invoice_id": "INV-....",
      "employee_id": "...",
      "expense_date": "YYYY-MM-DD",
      "vendor": "...",
      "total_amount": float,
      "currency": "INR",
      "items": [ {description, category, amount, currency, merchant, city}, ... ],
      "raw": <original JSON>
    }
    """
    # invoice id / number guess
    invoice_id = (
        raw_json.get("invoice_number") or raw_json.get("invoice_no") or raw_json.get("invoice_id")
        or raw_json.get("bill_no") or raw_json.get("receipt_no") or f"INV-{os.urandom(4).hex().upper()}"
    )
    emp_id = raw_json.get("Employee ID") or raw_json.get("employee_id") or fallback_emp_id or "UNKNOWN"
    d = _safe_date(raw_json)
    payload = {
        "invoice_id": str(invoice_id),
        "employee_id": str(emp_id),
        "expense_date": d.isoformat(),
        "vendor": _safe_vendor(raw_json),
        "total_amount": _safe_total(raw_json),
        "currency": _safe_currency(raw_json),
        "items": _safe_items(raw_json),
        "raw": raw_json
    }
    return payload

# -------------------- Single-file extractors (PDF / Image paths) --------------------
def extract_file_to_payload(
    file_path: str,
    emp_id_hint: Optional[str] = None,
    out_dir: str = "json_out",
    save_json_file: bool = True
) -> Dict[str, Any]:
    """
    Auto-detect by extension; call your extractors; normalize; optionally save JSON next to out_dir.
    Returns the normalized payload dict.
    """
    p = Path(file_path)
    ext = p.suffix.lower()
    if not p.exists():
        raise FileNotFoundError(f"Not found: {file_path}")

    if ext == ".pdf":
        j = extract_json_from_pdf_text(str(p), emp_id = emp_id_hint or "UNKNOWN")
        # your pdf extractor doesn't add emp id; thread it if given
        if emp_id_hint and "Employee ID" not in j:
            j["Employee ID"] = emp_id_hint
    elif ext in SUPPORTED_IMAGES:
        j = extract_json_from_image(str(p), emp_id=emp_id_hint or "UNKNOWN")
        if emp_id_hint and "Employee ID" not in j:
            j["Employee ID"] = emp_id_hint

    else:
        raise ValueError(f"Unsupported file type: {ext}. Convert PSD to PNG/JPG or use PDF.")

    # persist raw json (your function names the file using original image_name stem)
    if save_json_file:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        save_json(j, out_dir, p.name)

    # normalized output for downstream
    # return _normalize_payload(j, fallback_emp_id=emp_id_hint)
    return j

# --------------------------- Batch helpers (directory/glob) ---------------------------
def batch_extract_to_payloads(
    pattern: str,
    emp_id_hint: Optional[str] = None,
    out_dir: str = "json_out",
    save_json_file: bool = True
) -> List[Dict[str, Any]]:
    """
    pattern can be a glob like 'data/*.pdf' or 'invoices/**/*.*' (with recursive=True if using glob.glob)
    """
    paths = sorted(glob.glob(pattern, recursive=True))
    results = []
    for path in paths:
        try:
            payload = extract_file_to_payload(path, emp_id_hint=emp_id_hint, out_dir=out_dir, save_json_file=save_json_file)
            results.append(payload)
        except Exception as e:
            results.append({
                "file": path,
                "error": str(e)
            })
    return results

# --------------------------- Pretty printer for quick checks --------------------------
def show_payload_summary(payload: Dict[str, Any], max_items: int = 5):
    print(f"Invoice ID   : {payload.get('invoice_id')}")
    print(f"Employee ID  : {payload.get('employee_id')}")
    print(f"Date         : {payload.get('expense_date')}")
    print(f"Vendor       : {payload.get('vendor')}")
    print(f"Total        : {payload.get('total_amount')} {payload.get('currency')}")
    items = payload.get("items", [])
    print(f"Items ({len(items)})  :")
    for i, it in enumerate(items[:max_items], 1):
        print(f"  {i}. {it['description']} | {it['category']} | {it['amount']} {it['currency']} | {it.get('merchant') or ''} {('('+it['city']+')') if it.get('city') else ''}")
    if len(items) > max_items:
        print(f"  ... {len(items)-max_items} more")



# =========================
# AGENT IMPLEMENTATIONS
# =========================

# --- NEW/UPDATED EXTRACTOR AGENT (uses your ie.py) ---
import tempfile, pathlib, shutil
import image_extraction as  ie  # <- this is your module that contains extract_json_from_image, extract_json_from_pdf_text, save_json

class ExtractorAgent:

    SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".tiff"}

    def __init__(self, json_out_dir: str = "json_out"):
        self.json_out_dir = json_out_dir
        pathlib.Path(self.json_out_dir).mkdir(parents=True, exist_ok=True)

    def _write_temp_file(self, file_bytes: bytes, filename: str) -> str:
        suffix = pathlib.Path(filename).suffix or ".bin"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(file_bytes)
        return tmp_path

    def _is_pdf(self, path: str) -> bool:
        return pathlib.Path(path).suffix.lower() == ".pdf"

    def _is_supported_image(self, path: str) -> bool:
        return pathlib.Path(path).suffix.lower() in self.SUPPORTED_IMAGES

    def extract_from_file(self, file_bytes: bytes, filename: str, employee_id_hint: str | None) -> ExtractionResult:
        tmp_path = self._write_temp_file(file_bytes, filename)
        ext = pathlib.Path(filename).suffix.lower()

        try:
            if self._is_pdf(tmp_path):
                # --- PDF path ---
                j = ie.extract_json_from_pdf_text(tmp_path)
                # Add employee id if present (your pdf extractor doesn’t add it)
                if employee_id_hint:
                    j.setdefault("Employee ID", employee_id_hint)
                # persist JSON
                ie.save_json(j, self.json_out_dir, filename)
                payload = InvoicePayload(
                    employee_id=j.get("Employee ID") or employee_id_hint or "UNKNOWN",
                    expense_date=_safe_date(j),
                    vendor=_safe_vendor(j),
                    total_amount=_safe_total(j),
                    currency=j.get("currency", "INR"),
                    items=_safe_items(j),
                )
                return ExtractionResult(payload=payload, raw_text_preview=None, ocr_engine="gpt-4o-mini/pdf")

            elif self._is_supported_image(tmp_path):
                # --- Image path ---
                emp_id = employee_id_hint 

                print(f"ExtractorAgent: Processing image for Employee ID: {emp_id}")
                j = ie.extract_json_from_image(tmp_path, emp_id=emp_id)

                print(f"ExtractorAgent: Extracted JSON: {j}")
                # persist JSON
                ie.save_json(j, self.json_out_dir, filename)
                payload = InvoicePayload(
                    employee_id=j.get("Employee ID") or emp_id,
                    expense_date=_safe_date(j),
                    vendor=_safe_vendor(j),
                    total_amount=_safe_total(j),
                    currency=j.get("currency", ""),
                    items=_safe_items(j),
                )
                return ExtractionResult(payload=payload, raw_text_preview=None, ocr_engine="gpt-4o-mini/image")

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type '{ext}'. Convert PSD to PNG/JPG or provide PDF."
                )
        finally:
            # clean up the temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def extract_from_json(self, payload: dict) -> ExtractionResult:
        # If you call /process/json, we trust the payload directly
        data = InvoicePayload(**payload)
        # Also save to out dir for consistency
        fname = f"{data.invoice_id}.json"
        ie.save_json(json.loads(data.json()), self.json_out_dir, fname)
        return ExtractionResult(payload=data, raw_text_preview=None, ocr_engine="json")


# ------------------------------- UPDATED LangGraph node -------------------------------

def detect_engine_from_ext(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return "gpt-4o-mini/pdf"
    return "gpt-4o-mini/image"


def make_extraction_result(payload, **kwargs):
    # which fields exist on the current class?
    try:
        allowed_fields = set(getattr(ExtractionResult, "model_fields").keys())  # pydantic v2
    except Exception:
        allowed_fields = set(getattr(ExtractionResult, "__fields__", {}).keys())  # pydantic v1
    # filter kwargs
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
    return ExtractionResult(payload=payload, **safe_kwargs)


def extract_node(state: dict) -> dict:
    """
    Inputs (state):
      - file_path: str (PDF or image path on disk)  [preferred in notebook]
      - OR json_payload: dict (already structured as our normalized payload schema)
      - employee_id_hint: Optional[str]
      - json_out_dir: Optional[str] (default 'json_out')
      - save_json_file: Optional[bool] (default True)

    Outputs (state):
      - extraction: ExtractionResult
    """
    json_out_dir = state.get("json_out_dir", "json_out")
    save_json_file = state.get("save_json_file", True)

    # if state.get("json_payload"):
    #     # If user already provides normalized JSON-like payload
    #     normalized = _normalize_payload(state["json_payload"], fallback_emp_id=state.get("employee_id_hint"))
    #     # payload = dict_to_invoice_payload(normalized)
    #     payload = normalized

    #     extraction = ExtractionResult(
    #         payload=payload,
    #         raw_text_preview=None,
    #         ocr_engine="json"
    #     )
    #     # Save the raw JSON if requested
    #     if save_json_file:
    #         save_json(state["json_payload"], json_out_dir, f"{payload.invoice_id}.json")
    #     state["extraction"] = extraction
    #     return state


    file_path = state.get("file_path")
    if not file_path:
        raise ValueError("extract_node expects either 'file_path' or 'json_payload' in the graph state.")

    # Use the notebook helpers to extract & normalize
    normalized = extract_file_to_payload(
        file_path=file_path,
        emp_id_hint=state.get("employee_id_hint"),
        out_dir=json_out_dir,
        save_json_file=save_json_file
    )
    # payload = dict_to_invoice_payload(normalized)
    payload = normalized
    print("----------------------------------------------------------------------------")
    print("Extracted payload:", payload)
    print("----------------------------------------------------------------------------")
    extraction = ExtractionResult(
        payload=payload,
        raw_text_preview=None,
        ocr_engine=detect_engine_from_ext(file_path)
    )


    ocr_engine_label = detect_engine_from_ext(file_path)
    state["extraction"] = make_extraction_result(
        payload=payload,
        ocr_engine=ocr_engine_label,                # pass the string label
        raw_text_preview=None
    )



    state["extraction"] = extraction

    
    return state


class ValidationAgent:

    HARD = "HARD"
    SOFT = "SOFT"

    def __init__(self, employees_df: pd.DataFrame, policies_df: pd.DataFrame, llm: Any = None):
        self.emp = employees_df.copy()
        self.policies = policies_df.copy()
        # Keep compatibility lists if your old schema had them; harmless if absent
        self.policies["allowed_merchants_list"] = (
            self.policies["allowed_merchants"].apply(comma_list)
            if "allowed_merchants" in self.policies.columns else [[] for _ in range(len(self.policies))]
        )
        self.policies["allowed_cities_list"] = (
            self.policies["allowed_cities"].apply(comma_list)
            if "allowed_cities" in self.policies.columns else [[] for _ in range(len(self.policies))]
        )
        # LLM (JSON mode)
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        ).bind(response_format={"type": "json_object"})

    def _employee_row(self, employee_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not employee_id or "employee_id" not in self.emp.columns:
            return None
        rec = self.emp[self.emp["employee_id"] == employee_id]
        return None if rec.empty else rec.iloc[0].to_dict()

    def _compact_policies(self) -> List[Dict[str, Any]]:
        # Keep only relevant columns for prompting; tolerate missing columns
        keep = [c for c in [
            "policy_id","category","max_allowance","per_diem","applicable_grades","currency",
            "requires_receipt","allowed_merchants","allowed_cities","hard_enforced","notes"
        ] if c in self.policies.columns]
        return self.policies[keep].to_dict(orient="records")

    def _payload_to_dict(self, inv: "InvoicePayload") -> Dict[str, Any]:
        # Pydantic v1/v2 compatibility: model_dump or dict
        if hasattr(inv, "model_dump"):
            return inv.model_dump()
        return inv.dict()

    def _safe_items_sum(self, inv: "InvoicePayload") -> float:
        items = getattr(inv, "items", None) or []
        try:
            return round(sum(float(getattr(it, "amount", 0.0) or 0.0) for it in items), 2)
        except Exception:
            return 0.0

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text if isinstance(text, str) else json.dumps(text))
        except Exception:
            s, e = text.find("{"), text.rfind("}")
            if s != -1 and e != -1 and e > s:
                return json.loads(text[s:e+1])
            raise

    def validate(self, inv: "InvoicePayload") -> ValidationResult:

        emp_row = self._employee_row(inv.employee_id)
        policies = self._compact_policies()
        inv_dict = self._payload_to_dict(inv)

  

        # Provide the LLM with a crisp JSON spec for output
        INSTRUCTIONS = (

        "You are an **Expense Policy Validation Agent**. "
            "Your goal is to evaluate an invoice against the employee’s details and applicable company policies.\n\n"

            "### Decision Logic:\n"
            "- If the employee record is **missing or inactive**, mark as `Reject` (HARD).\n"
            f"- Apply grade and category-specific policy rules to each invoice item with {inv_dict} and emp data {emp_row} and policies {policies} based on this comparision perform analysis \n"
            "- For each invoice item, identify its **category** from  inv_dict  like Hotel, Travel, Food, rest in Others and compare it against policy rules for that employee's **grade**.\n"
            "- If `max_allowance` exists and the item or total amount **exceeds it**, create a HARD finding and set decision = 'Reject'.\n"
            "- If the invoice is within all limits and no findings exist, set decision = 'Approved'.\n"
            "- Always provide reasoning for your decision in at least one finding message. with emp details and respective policy detail\n\n"

            "### Notes:\n"
            "- Include the employee’s grade, policy category, and compared values in each finding’s context.\n"
            "- Always compare amounts numerically and ensure currency consistency.\n"
            "- Be concise and structured. Return ONLY valid JSON — no explanations, markdown, or extra text."
        )

        # Build prompt content
        prompt = {
        f"invoice_payload = {inv_dict}\n"
        f"employee_record = {emp_row}\n"
        f"policies = {policies}\n\n"
        }


        # Invoke LLM
        try:
            resp = self.llm.invoke([HumanMessage(content=[
                {"type": "text", "text": INSTRUCTIONS},
                {"type": "text", "text": json.dumps(prompt, default=str)}
            ])])
            raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
            out = self._parse_json(raw)
        except Exception as e:
            # LLM failed: conservative fallback
            return ValidationResult(
                decision=Decision.SEND_FOR_VALIDATION,
                findings=[ValidationFinding(rule_id="LLM-000", severity=self.SOFT,
                                            message="LLM validation unavailable; manual review required",
                                            context={"error": str(e)})],
                policy_rows_applied=[],
                employee_row=emp_row,
                computed={"payload_total": getattr(inv, "total_amount", None) or getattr(inv, "total", None),
                          "items_sum": self._safe_items_sum(inv)}
            )

        # Map LLM output → ValidationResult
        decision_str = (out.get("decision") or "").strip()
        if decision_str not in {"Approved", "Reject", "Send for validation"}:
            decision_str = "Test Node"

        findings = []
        for f in (out.get("findings") or []):
            try:
                findings.append(ValidationFinding(
                    rule_id=str(f.get("rule_id") or "LLM"),
                    severity=(str(f.get("severity") or self.SOFT).upper()),
                    message=str(f.get("message") or ""),
                    context=f.get("context") or {}
                ))
            except Exception:
                # tolerate any malformed finding
                continue

        policy_rows_applied = out.get("policy_rows_applied") or []
        # If LLM returned full rows, keep them; if ids only, keep as ids in context
        if policy_rows_applied and isinstance(policy_rows_applied[0], (str, int)):
            policy_rows_applied = [{"policy_id": pid} for pid in policy_rows_applied]

        computed = out.get("computed") or {}
        # Ensure computed has at least totals
        computed.setdefault("payload_total", getattr(inv, "total_amount", None) or getattr(inv, "total", None))
        computed.setdefault("items_sum", self._safe_items_sum(inv))

        # Final object
        decision = Decision.APPROVED if decision_str == "Approved" else (
            Decision.REJECT if decision_str == "Reject" else Decision.SEND_FOR_VALIDATION
        )
        return ValidationResult(
            decision=decision,
            findings=findings,
            policy_rows_applied=policy_rows_applied,
            employee_row=emp_row,
            computed=computed
        )


# ===================== VALIDATOR NODE =====================

def validate_node(state: dict) -> dict:
    """
    LangGraph node: runs ValidationAgent on the extracted invoice.
    Input:
        state["extraction"] -> ExtractionResult (from Extractor)
    Output:
        state["validation"] -> ValidationResult
    """
    extraction = state.get("extraction")
    if not extraction or not getattr(extraction, "payload", None):
        raise ValueError("No extraction payload found in state. Run extract_node first.")

    payload = extraction.payload

    emp_id = payload.employee_id
    if not emp_id:
        raise ValueError("Extraction payload missing employee_id; cannot validate.")
    

    # ---------------- Employee & Policy Data ----------------
    # Option 1: From database
    # employees_df = pd.read_sql("SELECT * FROM employees;", engine)
    # policies_df  = pd.read_sql("SELECT * FROM expense_policies;", engine)

    # Option 2: For testing, local mock data

   
    employees_df =  load_employees_df(emp_id)

    # employees_df['first_name']
    # employees_df['last_name']
    # employees_df['email']
    # employees_df['department']
    # employees_df['cost_center']
    # employees_df['grade']
    # employees_df['manager_id']

    policies_df = load_policies_df(employees_df['grade'].iloc[0])

    # ---------------- Validation ----------------
    validator = ValidationAgent(employees_df, policies_df)
    result = validator.validate(payload)

    # ---------------- Save into state ----------------
    state["validation"] = result
    state["decision"] = result.decision.value

    print(f"✅ Validation complete: {result.decision.value}")
    return state


# =========================
# LANGGRAPH STATE
# =========================
class GraphState(TypedDict, total=False):
    # inputs
    file_bytes: bytes
    file_name: str
    json_payload: Dict[str, Any]
    employee_id_hint: Optional[str]

    # shared resources (cached)
    employees_df: pd.DataFrame
    policies_df: pd.DataFrame

    # intermediates
    extraction: ExtractionResult
    validation: ValidationResult

    # outputs
    decision: Decision
    process_id: str


# =========================
# NODE IMPLEMENTATIONS
# =========================
def load_caches_node(state: GraphState) -> GraphState:
    state["employees_df"] = load_employees_df()
    state["policies_df"] = load_policies_df()
    return state



# ===================== Decision Router & Handlers =====================

from typing import Literal
from langgraph.graph import StateGraph, END

def route_decision(state: dict) -> Literal["approved", "reject", "manual"]:
    """
    Reads state["validation"].decision and returns one of:
      - "approved"
      - "reject"
      - "manual"  (Send for validation)
    """
    if "validation" not in state or not getattr(state["validation"], "decision", None):
        raise ValueError("route_decision expects state['validation'] with a decision. Run validate_node first.")

    decision = state["validation"].decision.value if hasattr(state["validation"].decision, "value") \
               else str(state["validation"].decision)

    if decision == " ":
        return "approved"
    elif decision == "Reject":
        return "reject"
    else:
        # "Send for validation" or anything else defaults to manual review path
        return "manual"


def approved_node(state: dict) -> dict:
    """Finalize for approved path."""
    state["tag"] = "Approved"
    # (optional) add audit info here, e.g., state["audit"].append(...)
    print("✅ Routed: Approved")
    return state


def reject_node(state: dict) -> dict:
    """Finalize for reject path."""
    state["tag"] = "Reject"
    # (optional) add audit info here
    print("⛔ Routed: Reject")
    return state


def manual_review_node(state: dict) -> dict:
    """Finalize for manual validation path."""
    state["tag"] = "Send for validation"
    # (optional) enqueue task / notify reviewer here
    print("🕵️ Routed: Send for validation")
    return state



# ===================== Build the Graph =====================

# graph_builder = StateGraph(dict)
graph_builder = StateGraph(dict)

# existing nodes
graph_builder.add_node("extract", extract_node)
graph_builder.add_node("validate", validate_node)

# router + handlers
graph_builder.add_node("approved", approved_node)
graph_builder.add_node("reject", reject_node)
graph_builder.add_node("manual_review", manual_review_node)

# entry + edges
graph_builder.set_entry_point("extract")
graph_builder.add_edge("extract", "validate")


# graph_builder.add_edge("validate", END)
# conditional routing based on validation decision
graph_builder.add_conditional_edges(
    "validate",
    route_decision,
    {
        "approved": "approved",
        "reject": "reject",
        "manual": "manual_review",
    },
)

# all terminal nodes end the graph
graph_builder.add_edge("approved", END)
graph_builder.add_edge("reject", END)
graph_builder.add_edge("manual_review", END)

graph = graph_builder.compile()



state = {
    # "file_path":"input/pdf/hotel_pdfs/hotel_invoice_02.pdf" ,   # " , "input/pdf/meal_pdfs/meals/meal_receipt_01.pdf" , "input/pdf/stationary_pdfs/stationary/stationary_invoice_02.pdf" ,"input/pdf/air_travel_pdfs/air_travel/air_invoice_03.pdf"
    "file_path": "input/images/stationery_only/stationery_invoice_02.png" ,   # "input/images/hotels_v3/agoda_invoice_42.png" ,"input/images/meals_only/meal_receipt_07.png" , "input/images/ride_invoices_customers/generated_ride_invoices_customers/ola_invoice_003.png"
    "employee_id_hint": "E1024",
    "json_out_dir": "output/langgraph_json",
    "save_json_file": True
}

      
final_state = graph.invoke(state)

print("Final tag :", final_state.get("tag"))
print("Decision  :", final_state["validation"].decision.value)
# Optional: inspect findings
for f in final_state["validation"].findings:
    print(f"- [{f.severity}] {f.rule_id}: {f.message}")  