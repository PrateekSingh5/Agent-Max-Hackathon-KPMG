# agent.py
import os
import io
import uuid
import json
import enum
import datetime as dt
from typing import List, Optional, Dict, Any, Literal, TypedDict

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import create_engine, text

# =========================
# ENV & DB
# =========================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://myuser:rootpassword@localhost:5432/agent_max")
engine = create_engine(DATABASE_URL, future=True)

# =========================
# LLM / Vision Imports
# =========================
import base64
import glob
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import fitz  # PyMuPDF
from fastapi import HTTPException

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Vision / JSON-mode model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY).bind(
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
    "Do NOT add commentary. Do NOT wrap in markdown—return only JSON. "
    "- If a field is missing, simply omit it (do not invent data). "
    "- Include important fields you can infer from text (seller, address, contact, invoice_no/date/due, line_items_summary, amounts, instructions). "
    "- Deduplicate and correct minor OCR spacing like 'HonkKong' -> 'Hong Kong', 'DueDate:' -> 'due date'. "
    "- If bill is for travel get from and to locations. "
    "- If bill is for hotel get hotel name, location, check in, check out and from and till. "
    "- Tag currency if possible (e.g., USD, EUR, GBP, INR). "
    "- Tag category of bill (e.g., travel, hotel, food, office supplies, others) with key 'category'. "
    "- Tag vendor name like: ola, uber, Airbnb, agoda, booking.com, cleartrip, easemytrip, go ibibo, Yatra, mmt, Indigo, Airasia, etc. "
    "- Tag Total Amount / Amount Paid / Total Paid / Grand Total with key 'total_amount'."
)

def extract_json_from_image(image_path: str, emp_id: str) -> dict:
    msg = HumanMessage(
        content=[
            {"type": "text", "text": INSTRUCTIONS_IMAGE},
            {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
        ]
    )
    resp = llm.invoke([msg])
    raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    try:
        data = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start:end + 1])
        else:
            raise ValueError(f"Model did not return valid JSON:\n{raw}")
    # ensure employee id is present
    data.setdefault("Employee ID", emp_id)
    return data

def save_json(data, out_dir, image_name):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (Path(image_name).stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {Path(out_path).name} -> {out_path}")

# ---------------------------------------For PDF -----------------------------
INSTRUCTIONS_PDF = (
    "You are an expert at parsing invoice or receipt text. "
    "I will give you the raw text extracted from a PDF document. "
    "Return a SINGLE JSON object with fields that appear (e.g., 'invoice_number', 'date', 'seller', 'buyer', 'items', 'total', 'tax', etc.). "
    "Represent line items or tables as arrays of row objects. "
    "Prefer numbers for numeric values, ISO date format for dates, and omit missing fields. "
    "If it's a travel bill, extract 'from' and 'to' locations; if it's a hotel bill, extract 'hotel_name', "
    "'location', 'check_in', and 'check_out'. Tag currency like INR, USD, etc. "
    "Return only valid JSON, no explanations. "
    "- If bill is for travel get from and to locations. "
    "- If bill is for hotel get hotel name, location, check in, check out and from and till. "
    "- Tag currency if possible (e.g., USD, EUR, GBP, INR). "
    "- Tag category of bill (e.g., travel, hotel, food, office supplies, others) with key 'category'."
)

def read_pdf_text(pdf_path: str) -> str:
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text.strip()

def extract_json_from_pdf_text(pdf_path: str, emp_id: str) -> dict:
    pdf_text = read_pdf_text(pdf_path)
    msg = HumanMessage(
        content=[
            {"type": "text", "text": f"{INSTRUCTIONS_PDF}\n\nDocument Text:\n{pdf_text}"},
        ]
    )
    resp = llm.invoke([msg])
    raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    try:
        data = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start:end + 1])
        else:
            raise ValueError(f"Invalid JSON returned:\n{raw}")
    data.setdefault("Employee ID", emp_id)
    return data

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

# --------- Helpers / Normalization ---------
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".tiff"}

def _to_float(x) -> float:
    """Parse currency-like strings into float; fallback 0.0 on failure."""
    if x is None:
        return 0.0
    s = str(x).strip()
    try:
        return float(s)
    except Exception:
        pass
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(cleaned) if cleaned not in {"", ".", "-", "-.", ".-"} else 0.0
    except Exception:
        return 0.0

def _parse_date_any(s: str) -> Optional[dt.date]:
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return dt.datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    try:
        return dt.date.fromisoformat(s[:10])
    except Exception:
        return None

def _safe_date(j: Dict[str, Any]) -> dt.date:
    for k in ["invoice_date", "date", "bill_date", "issue_date", "created_on", "dated"]:
        if k in j and j[k]:
            d = _parse_date_any(j[k])
            if d:
                return d
    return dt.date.today()

def _safe_currency(j: Dict[str, Any]) -> str:
    return str(j.get("currency", "INR")).upper()

def _safe_vendor(j: Dict[str, Any]) -> Optional[str]:
    # direct flat keys
    for k in ["vendor", "merchant", "company", "hotel_name", "restaurant_name", "airline"]:
        if j.get(k):
            return str(j[k])
    # nested dicts
    for k in ["seller", "vendor", "merchant", "company"]:
        v = j.get(k)
        if isinstance(v, dict):
            for kk in ["hotel_name", "name", "legal_name", "display_name", "brand"]:
                if v.get(kk):
                    return str(v[kk])
        if isinstance(v, str) and v.strip():
            return v.strip()
    # filename hint
    fname = (j.get("_source_file") or j.get("_file_name") or "").strip()
    if fname:
        stem = Path(fname).stem
        if stem:
            return stem.replace("_", " ").replace("-", " ").title()
    return None

def infer_category(j: Dict[str, Any]) -> Optional[str]:
    # structure hints
    if isinstance(j.get("booking_details"), dict) or any(k in j for k in ["check_in", "check_out", "hotel_name"]):
        return "Hotel"
    if any(k in j for k in ["from", "to", "pnr", "airline", "flight_no", "ticket_no"]):
        return "Travel"
    if any(k in j for k in ["restaurant_name", "meal", "food", "dining"]):
        return "Food"
    if any(k in j for k in ["stationery", "office supplies", "pen", "paper", "notebook", "stapler"]):
        return "Office Supplies"

    # item text hints
    items = j.get("items") or j.get("line_items") or []
    for it in items:
        blob = " ".join(str(it.get(k, "")) for k in ["description", "category", "item"]).lower()
        if any(w in blob for w in ["meal", "food", "restaurant", "dinner", "lunch"]):
            return "Food"
        if any(w in blob for w in ["hotel", "room", "stay", "lodging"]):
            return "Hotel"
        if any(w in blob for w in ["ticket", "flight", "airline", "uber", "ola", "cab", "taxi", "ride"]):
            return "Travel"
        if any(w in blob for w in ["stationery", "pen", "paper", "notebook", "ink", "file"]):
            return "Office Supplies"

    # filename hints
    fname = (j.get("_source_file") or j.get("_file_name") or "").lower()
    if any(w in fname for w in ["hotel", "agoda", "oyo", "stay", "lodg"]):
        return "Hotel"
    if any(w in fname for w in ["air", "flight", "ticket", "indigo", "airindia", "vistara", "goair", "spicejet"]):
        return "Travel"
    if any(w in fname for w in ["uber", "ola", "ride", "cab", "taxi"]):
        return "Travel"
    if any(w in fname for w in ["stationery", "stationary", "office"]):
        return "Office Supplies"
    return None

# LLM total helper
def llm_compute_total(j: Dict[str, Any], model=None) -> Optional[float]:
    m = model or llm
    INSTR = (
        "You are a billing calculator. Given JSON-like bill data, return ONLY JSON with:\n"
        "{\n"
        '  "total": <number>,\n'
        '  "currency": "<ISO like INR/USD/EUR or best guess>"\n'
        "}\n"
        "Rules:\n"
        "- total = (subtotal or sum(line items)) + taxes/fees - discounts/credits/advance.\n"
        "- If multiple taxes/fees, add all. If amount_due exists, prefer it.\n"
        "- If values have symbols (₹, $, commas), still compute as number.\n"
        "- If impossible, return total: 0."
    )
    try:
        msg = HumanMessage(content=[
            {"type": "text", "text": INSTR + "\nBill JSON:\n" + json.dumps(j, default=str)}
        ])
        resp = m.invoke([msg])
        raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
        s, e = raw.find("{"), raw.rfind("}")
        data = json.loads(raw if s == -1 else raw[s:e + 1])
        t = data.get("total") or data.get("amount_due") or data.get("grand_total")
        c = data.get("currency")
        if c and not j.get("currency"):
            j["currency"] = c
        if t is not None:
            return _to_float(t)
    except Exception:
        pass
    return None

# NOTE: _safe_items and _safe_total must avoid mutual recursion
def _safe_items(j: Dict[str, Any], add_fallback_total: bool = True) -> List[Dict[str, Any]]:
    """
    Extract normalized line items from the source JSON.
    If none found and add_fallback_total=True, create a single 'Total' row
    using _safe_total(..., use_items=False) to avoid recursion.
    """
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
            cat = row.get("category") or j.get("category") or "Uncategorized"
            amt = _to_float(row.get("amount") or row.get("price") or row.get("total") or 0)
            cur = (row.get("currency") or j.get("currency") or "INR")
            merch = row.get("merchant") or j.get("seller") or j.get("vendor")
            city = row.get("city") or j.get("city")
            out.append({
                "description": str(desc),
                "category": str(cat),
                "amount": amt,  # already float
                "currency": str(cur).upper(),
                "merchant": merch if merch else None,
                "city": city if city else None
            })

    if not out and add_fallback_total:
        out.append({
            "description": "Total",
            "category": str(j.get("category", "Uncategorized")),
            "amount": _safe_total(j, try_llm=False, use_items=False),
            "currency": _safe_currency(j),
            "merchant": j.get("seller") or j.get("vendor"),
            "city": j.get("city")
        })
    return out

def _safe_total(j: Dict[str, Any], try_llm: bool = True, use_items: bool = True) -> float:
    """
    Compute a robust total:
      1) Prefer explicit fields
      2) Else, optionally sum line items (if use_items=True)
      3) Else, LLM fallback (if try_llm=True)
    """
    for k in ["amount_due", "total", "grand_total", "total_amount", "net_total", "invoice_total"]:
        if k in j and j[k] is not None:
            val = _to_float(j[k])
            if val > 0:
                return val

    if use_items:
        items = _safe_items(j, add_fallback_total=False)
        if items:
            sum_items_val = round(sum(_to_float(it.get("amount", 0)) for it in items), 2)
            if sum_items_val > 0:
                return sum_items_val

    if try_llm:
        t = llm_compute_total(j)
        if t is not None and t > 0:
            return round(float(t), 2)

    return 0.0

def _normalize_payload(raw_json: Dict[str, Any], fallback_emp_id: Optional[str]) -> Dict[str, Any]:
    invoice_id = (
        raw_json.get("invoice_number") or raw_json.get("invoice_no") or raw_json.get("invoice_id")
        or raw_json.get("bill_no") or raw_json.get("receipt_no") or f"INV-{os.urandom(4).hex().upper()}"
    )
    emp_id = raw_json.get("Employee ID") or raw_json.get("employee_id") or fallback_emp_id or "UNKNOWN"
    d = _safe_date(raw_json)
    return {
        "invoice_id": str(invoice_id),
        "employee_id": str(emp_id),
        "expense_date": d.isoformat(),
        "vendor": _safe_vendor(raw_json),
        "total_amount": _safe_total(raw_json),
        "currency": _safe_currency(raw_json),
        "items": _safe_items(raw_json),
        "raw": raw_json
    }

class InvoicePayload(BaseModel):
    # canonical fields
    invoice_id: Optional[str] = Field(default_factory=lambda: f"INV-{uuid.uuid4().hex[:8].upper()}")
    employee_id: Optional[str] = None
    expense_date: Optional[dt.date] = None
    vendor: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    items: List[InvoiceItem] = Field(default_factory=list)

    # raw-ish fields
    invoice_number: Optional[str] = None
    date: Optional[dt.date] = None
    seller: Optional[Seller] = None
    buyer: Optional[Buyer] = None
    booking_details: Optional[BookingDetails] = None
    total: Optional[float] = None
    category: Optional[str] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    def _map_raw_to_canonical(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return v
        out = dict(v)

        # basic mappings
        if not out.get("invoice_id"):
            out["invoice_id"] = v.get("invoice_number") or out.get("invoice_id")
        if not out.get("employee_id"):
            out["employee_id"] = v.get("Employee ID") or v.get("employee_id")
        if not out.get("expense_date"):
            out["expense_date"] = v.get("date")

        # vendor (fill if missing/falsy)
        if not out.get("vendor"):
            try:
                out["vendor"] = _safe_vendor(v)
            except Exception:
                seller = v.get("seller")
                if isinstance(seller, dict):
                    out["vendor"] = seller.get("hotel_name") or seller.get("name")

        # category inference (fill if missing/falsy)
        if not out.get("category"):
            try:
                out["category"] = infer_category(v)
            except Exception:
                pass

        # totals: coerce and LLM fallback if needed
        if v.get("total") is not None:
            out["total"] = _to_float(v.get("total"))
        else:
            out["total"] = _safe_total(v, try_llm=False)

        if v.get("total_amount") is not None:
            out["total_amount"] = _to_float(v.get("total_amount"))
        else:
            out["total_amount"] = _safe_total(v, try_llm=False)

        if (out.get("total_amount") in (None, 0.0)) and (out.get("total") in (None, 0.0)):
            t_llm = _safe_total(v, try_llm=True)  # one-shot LLM compute
            if t_llm and t_llm > 0:
                out["total"] = t_llm
                out["total_amount"] = t_llm

        # currency default
        if not out.get("currency"):
            out["currency"] = (str(v.get("currency") or "INR")).upper()

        # items ensure populated
        items_src = v.get("items")
        if not isinstance(items_src, list) or len(items_src) == 0:
            try:
                out["items"] = _safe_items(v)
            except Exception:
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
        if v is None:
            return v
        if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
            return v
        try:
            if isinstance(v, str):
                v = v.split("T")[0]
            return dt.date.fromisoformat(str(v))
        except Exception:
            try:
                return dt.datetime.fromisoformat(str(v)).date()
            except Exception:
                return None

    @field_validator("seller", mode="before")
    def _coerce_seller(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            return {"hotel_name": v}
        return None

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
def load_employees_df(emp_id: str) -> pd.DataFrame:
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
    return round(sum(i.amount for i in items if i.amount), 2)

def load_employee_by_email(email: str) -> Optional[Dict[str, Any]]:
    query = text("SELECT * FROM employees WHERE email = :email;")
    with engine.connect() as conn:
        result = conn.execute(query, {"email": email}).mappings().first()
        return dict(result) if result else None

# -------------------- File extractors (PDF / Image paths) --------------------
def extract_file_to_payload(
    file_path: str,
    emp_id_hint: Optional[str] = None,
    out_dir: str = "json_out",
    save_json_file: bool = True
) -> Dict[str, Any]:
    p = Path(file_path)
    ext = p.suffix.lower()
    if not p.exists():
        raise FileNotFoundError(f"Not found: {file_path}")

    if ext == ".pdf":
        j = extract_json_from_pdf_text(str(p), emp_id=emp_id_hint or "UNKNOWN")
        j["_source_file"] = p.name
    elif ext in SUPPORTED_IMAGES:
        j = extract_json_from_image(str(p), emp_id=emp_id_hint or "UNKNOWN")
        j["_source_file"] = p.name
    else:
        raise ValueError(f"Unsupported file type: {ext}. Convert PSD to PNG/JPG or use PDF.")

    if emp_id_hint and "Employee ID" not in j:
        j["Employee ID"] = emp_id_hint

    if save_json_file:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        save_json(j, out_dir, p.name)

    return j  # keep raw for now; InvoicePayload coercion happens later

# --------------------------- Batch helpers ---------------------------
def batch_extract_to_payloads(pattern: str, emp_id_hint: Optional[str] = None,
                              out_dir: str = "json_out", save_json_file: bool = True) -> List[Dict[str, Any]]:
    paths = sorted(glob.glob(pattern, recursive=True))
    results = []
    for path in paths:
        try:
            payload = extract_file_to_payload(path, emp_id_hint=emp_id_hint, out_dir=out_dir, save_json_file=save_json_file)
            results.append(payload)
        except Exception as e:
            results.append({"file": path, "error": str(e)})
    return results

# --------------------------- Pretty printer --------------------------
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
        print(f"  ... {len(items) - max_items} more")

# =========================
# AGENT IMPLEMENTATIONS
# =========================
import tempfile
import pathlib
import image_extraction as ie  # your module with extract_json_from_image/pdf and save_json

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

    def extract_from_file(self, file_bytes: bytes, filename: str, employee_id_hint: Optional[str]) -> ExtractionResult:
        tmp_path = self._write_temp_file(file_bytes, filename)
        ext = pathlib.Path(filename).suffix.lower()
        try:
            if self._is_pdf(tmp_path):
                j = ie.extract_json_from_pdf_text(tmp_path)
                if employee_id_hint:
                    j.setdefault("Employee ID", employee_id_hint)
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
                emp_id = employee_id_hint
                j = ie.extract_json_from_image(tmp_path, emp_id=emp_id)
                ie.save_json(j, self.json_out_dir, filename)
                payload = InvoicePayload(
                    employee_id=j.get("Employee ID") or emp_id,
                    expense_date=_safe_date(j),
                    vendor=_safe_vendor(j),
                    total_amount=_safe_total(j),
                    currency=j.get("currency", "INR"),
                    items=_safe_items(j),
                )
                return ExtractionResult(payload=payload, raw_text_preview=None, ocr_engine="gpt-4o-mini/image")
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Convert PSD to PNG/JPG or provide PDF.")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def extract_from_json(self, payload: dict) -> ExtractionResult:
        data = InvoicePayload(**payload)
        fname = f"{data.invoice_id}.json"
        ie.save_json(json.loads(data.json()), self.json_out_dir, fname)
        return ExtractionResult(payload=data, raw_text_preview=None, ocr_engine="json")

# ------------------------------- Graph nodes -------------------------------
def detect_engine_from_ext(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return "gpt-4o-mini/pdf" if ext == ".pdf" else "gpt-4o-mini/image"

def make_extraction_result(payload, **kwargs):
    try:
        allowed = set(getattr(ExtractionResult, "model_fields").keys())
    except Exception:
        allowed = set(getattr(ExtractionResult, "__fields__", {}).keys())
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    return ExtractionResult(payload=payload, **safe_kwargs)

def extract_node(state: dict) -> dict:
    json_out_dir = state.get("json_out_dir", "json_out")
    save_json_file = state.get("save_json_file", True)

    file_path = state.get("file_path")
    if not file_path:
        raise ValueError("extract_node expects 'file_path' in the state.")

    normalized = extract_file_to_payload(
        file_path=file_path,
        emp_id_hint=state.get("employee_id_hint"),
        out_dir=json_out_dir,
        save_json_file=save_json_file
    )

    # Coerce to InvoicePayload to apply validators (totals, vendor, category, etc.)
    payload = InvoicePayload(**normalized)

    print("----------------------------------------------------------------------------")
    print("Extracted payload (normalized):", payload.model_dump())
    print("----------------------------------------------------------------------------")

    extraction = ExtractionResult(
        payload=payload,
        raw_text_preview=None,
        ocr_engine=detect_engine_from_ext(file_path)
    )

    state["extraction"] = make_extraction_result(
        payload=payload,
        ocr_engine=extraction.ocr_engine,
        raw_text_preview=None
    )
    return state

# ===================== VALIDATION AGENT =====================
class ValidationAgent:
    HARD = "HARD"
    SOFT = "SOFT"

    def __init__(self, employees_df: pd.DataFrame, policies_df: pd.DataFrame, llm: Any = None):
        self.emp = employees_df.copy()
        self.policies = policies_df.copy()
        self.policies["allowed_merchants_list"] = (
            self.policies["allowed_merchants"].apply(comma_list)
            if "allowed_merchants" in self.policies.columns else [[] for _ in range(len(self.policies))]
        )
        self.policies["allowed_cities_list"] = (
            self.policies["allowed_cities"].apply(comma_list)
            if "allowed_cities" in self.policies.columns else [[] for _ in range(len(self.policies))]
        )
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0).bind(response_format={"type": "json_object"})

    def _employee_row(self, employee_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not employee_id or "employee_id" not in self.emp.columns:
            return None
        rec = self.emp[self.emp["employee_id"] == employee_id]
        return None if rec.empty else rec.iloc[0].to_dict()

    def _compact_policies(self) -> List[Dict[str, Any]]:
        keep = [c for c in [
            "policy_id", "category", "max_allowance", "per_diem", "applicable_grades", "currency",
            "requires_receipt", "allowed_merchants", "allowed_cities", "hard_enforced", "notes"
        ] if c in self.policies.columns]
        return self.policies[keep].to_dict(orient="records")

    def _payload_to_dict(self, inv: "InvoicePayload") -> Dict[str, Any]:
        return inv.model_dump() if hasattr(inv, "model_dump") else inv.dict()

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
                return json.loads(text[s:e + 1])
            raise

    def validate(self, inv: "InvoicePayload") -> ValidationResult:
        emp_row = self._employee_row(inv.employee_id)
        policies = self._compact_policies()
        inv_dict = self._payload_to_dict(inv)

        INSTRUCTIONS = (
            "You are an **Expense Policy Validation Agent**. "
            "Evaluate the invoice against employee details and applicable policies.\n\n"
            "Decision Logic:\n"
            "- If the employee record is missing or inactive, mark as `Reject` (HARD).\n"
            f"- Apply grade and category-specific policy rules to each invoice item with invoice={inv_dict}, employee={emp_row}, policies={policies}.\n"
            "- For each item, infer category (Hotel/Travel/Food/Others) if missing and compare against grade policy.\n"
            "- If max_allowance exists and item or total exceeds it, create a HARD finding and set decision='Reject'.\n"
            "- If within limits and no findings, set decision='Approved'.\n"
            "- Provide reasoning in at least one finding message with employee details and policy context.\n"
            "Return JSON only."
        )

        try:
            resp = self.llm.invoke([HumanMessage(content=[
                {"type": "text", "text": INSTRUCTIONS}
            ])])
            raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
            out = self._parse_json(raw)
        except Exception as e:
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

        decision_str = (out.get("decision") or "").strip()
        if decision_str not in {"Approved", "Reject", "Send for validation"}:
            decision_str = "Send for validation"

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
                continue

        policy_rows_applied = out.get("policy_rows_applied") or []
        if policy_rows_applied and isinstance(policy_rows_applied[0], (str, int)):
            policy_rows_applied = [{"policy_id": pid} for pid in policy_rows_applied]

        computed = out.get("computed") or {}
        computed.setdefault("payload_total", getattr(inv, "total_amount", None) or getattr(inv, "total", None))
        computed.setdefault("items_sum", self._safe_items_sum(inv))

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
    extraction = state.get("extraction")
    if not extraction or not getattr(extraction, "payload", None):
        raise ValueError("No extraction payload found in state. Run extract_node first.")

    payload = extraction.payload
    emp_id = payload.employee_id
    if not emp_id:
        raise ValueError("Extraction payload missing employee_id; cannot validate.")

    employees_df = load_employees_df(emp_id)
    policies_df = load_policies_df(employees_df['grade'].iloc[0])

    validator = ValidationAgent(employees_df, policies_df)
    result = validator.validate(payload)

    state["validation"] = result
    state["decision"] = result.decision.value

    print(f"✅ Validation complete: {result.decision.value}")
    return state

# =========================
# LANGGRAPH STATE & GRAPH
# =========================
class GraphState(TypedDict, total=False):
    file_bytes: bytes
    file_name: str
    json_payload: Dict[str, Any]
    employee_id_hint: Optional[str]
    employees_df: pd.DataFrame
    policies_df: pd.DataFrame
    extraction: ExtractionResult
    validation: ValidationResult
    decision: Decision
    process_id: str

def load_caches_node(state: GraphState) -> GraphState:
    # (unused in this flow; left for future cache preloads)
    return state

from typing import Literal
from langgraph.graph import StateGraph, END

def route_decision(state: dict) -> Literal["approved", "reject", "manual"]:
    if "validation" not in state or not getattr(state["validation"], "decision", None):
        raise ValueError("route_decision expects state['validation'] with a decision. Run validate_node first.")
    decision = state["validation"].decision.value if hasattr(state["validation"].decision, "value") else str(state["validation"].decision)
    if decision == "Approved":
        return "approved"
    elif decision == "Reject":
        return "reject"
    else:
        return "manual"

def approved_node(state: dict) -> dict:
    state["tag"] = "Approved"
    print("✅ Routed: Approved")
    return state

def reject_node(state: dict) -> dict:
    state["tag"] = "Reject"
    print("⛔ Routed: Reject")
    return state

def manual_review_node(state: dict) -> dict:
    state["tag"] = "Send for validation"
    print("🕵️ Routed: Send for validation")
    return state

graph_builder = StateGraph(dict)
graph_builder.add_node("extract", extract_node)
graph_builder.add_node("validate", validate_node)
graph_builder.add_node("approved", approved_node)
graph_builder.add_node("reject", reject_node)
graph_builder.add_node("manual_review", manual_review_node)

# graph_builder.set_entry_point("extract")
# graph_builder.add_edge("extract", "validate")

graph_builder.set_entry_point("validate")
# graph_builder.add_edge("extract", "validate")

graph_builder.add_conditional_edges(
    "validate",
    route_decision,
    {"approved": "approved", "reject": "reject", "manual": "manual_review"},
)

graph_builder.add_edge("approved", END)
graph_builder.add_edge("reject", END)
graph_builder.add_edge("manual_review", END)

graph = graph_builder.compile()

# ---------------------- Quick local test (optional) ----------------------
if __name__ == "__main__":
    state = {
        "file_path": "input/images/stationery_only/stationery_invoice_02.png",
        "employee_id_hint": "E1024",
        "json_out_dir": "output/langgraph_json",
        "save_json_file": True
    }

    final_state = graph.invoke(state)
    print("Final tag :", final_state.get("tag"))
    print("Decision  :", final_state["validation"].decision.value)
    for f in final_state["validation"].findings:
        print(f"- [{f.severity}] {f.rule_id}: {f.message}")
