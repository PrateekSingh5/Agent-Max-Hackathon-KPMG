# agent.py
import os
import uuid
import json
import datetime as dt
from typing import List, Optional, Dict, Any
import pandas as pd
import re
import base64
from pathlib import Path
from dotenv import load_dotenv

import fitz  # PyMuPDF
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import create_engine, text
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# external DB helper expected in PYTHONPATH
# from  db_utils import load_policies_df, load_employee_by_email 
import db_utils

# =========================================================
# ENV / MODEL INIT
# =========================================================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_READY = bool(OPENAI_API_KEY)

llm_json = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=OPENAI_API_KEY,
).bind(response_format={"type": "json_object"})

# DATABASE_URL = os.getenv(
#     "DATABASE_URL",
#     "postgresql://myuser:rootpassword@localhost:5432/agent_max"
# )
# engine = create_engine(DATABASE_URL, future=True)

# engine  = db_utils.engine
# =========================================================
# CONSTANTS / REGEX
# =========================================================
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}
SUPPORTED_PDF = {".pdf"}

ADDRESS_HINT_WORDS = [
    "address", "addr", "branch", "office", "head office",
    "registered office", "billing address", "location",
]

CITY_HINT_REGEX = re.compile(
    r"([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)\s*(?:-|,)?\s*(?:[A-Z]{2})?\s*(\d{5,6})?",
    re.MULTILINE,
)

INSTRUCTIONS_IMAGE = (
    "You are an expert at visually parsing invoices, receipts, cab bills, hotel bills, "
    "travel tickets, etc. You will see an image.\n"
    "Return ONLY ONE valid JSON object.\n\n"
    "REQUIRED TOP-LEVEL KEYS (include them all even if some values are null):\n"
    "  'invoice_number'          (string or null)\n"
    "  'date'                    (ISO 'YYYY-MM-DD' if you can infer, else null)\n"
    "  'currency'                (3-4 letter code like INR, USD, etc.)\n"
    "  'total_amount'            (final payable / amount due / grand total as a number)\n"
    "  'category'                ('Hotel', 'Travel', 'Food', 'Office Supplies', 'Others')\n"
    "  'seller': {\n"
    "      'name': <vendor / hotel / merchant / company / restaurant>,\n"
    "      'location': <city/branch/address text if visible, else null>\n"
    "  }\n"
    "  'items': [\n"
    "      { 'description': <string>, 'amount': <number>, 'currency': <string>, 'city': <string or null> }, ...\n"
    "  ]\n"
    "\n"
    "ALSO include any of these if present:\n"
    "  'hotel_name', 'check_in', 'check_out', 'from', 'to', 'booking_number', 'gst', 'tax', 'fare_breakdown'.\n\n"
    "Rules:\n"
    "- 'seller.name' MUST be present.\n"
    "- 'seller.location' SHOULD contain address/city/PIN if visible.\n"
    "- 'total_amount' numeric only.\n"
    "- 'date' in YYYY-MM-DD.\n"
    "- 'items' for line-level costs.\n"
    "- Respond with ONLY valid JSON."
)

INSTRUCTIONS_PDF = (
    "You are an expert invoice/receipt parser. I will send you raw text extracted from a PDF.\n"
    "Return ONLY ONE valid JSON object.\n\n"
    "REQUIRED KEYS:\n"
    "  'invoice_number', 'date', 'currency', 'total_amount', 'category', 'seller', 'items'\n"
    "ALSO include when present: 'hotel_name','check_in','check_out','from','to','booking_number','gst','tax'.\n"
    "Rules:\n"
    "- 'seller.name' MUST exist. 'seller.location' SHOULD exist.\n"
    "- Prefer Amount Due/Grand Total.\n"
    "- Respond with ONLY valid JSON."
)


# INSTRUCTIONS_VALIDATION = (
#     "You are an Expense Policy Validation Agent.\n\n"
#     "Your job: Decide how to route an expense claim and return ONLY ONE valid JSON object.\n\n"
#     "Inputs are employee, policy, and invoice objects.\n"
#     "Decision rules (use these exact tags/decisions):\n"
#     "- If spent <= allowed: tag = 'Auto Approved', decision = 'Approved'\n"
#     "- If percent over > 25%: tag = 'Rejected', decision = 'Reject'\n"
#     "- If percent over > 10% and < 25%: tag = 'Finance Pending', decision = 'Send to Finance Team'\n"
#     "- If percent over >= 0% and <= 10%: tag = 'Manager Pending', decision = 'Send to Manager'\n"
#     "- If policy is missing/invalid (no allowed_amount or not found): tag = 'Finance Pending', decision = 'Send to Finance Team'\n\n"
#     "Computations:\n"
#     "- allowed_amount := policy.max_allowance (number) or null if unavailable\n"
#     "- percent over := ((spent - allowed) / allowed) * 100; if allowed is null or 0, set percent_diff to null and use policy-missing branch\n"
#     "- Round percent_diff to 2 decimals\n\n"
#     "Output JSON shape:\n"
#     "{\n"
#     '  \"tag\": \"<Auto Approved | Finance Pending | Pending |  Rejected>\",\n'
#     '  \"decision\": \"<Approved | Send to Finance Team | Send to Manager | Reject>\",\n'
#     '  \"message\": \"<summary mentioning employee name or id, grade, spent vs allowed, reason>\",\n'
#     '  \"metrics\": {\n'
#     '    \"grade\": \"<employee.grade>\",\n'
#     '    \"category\": \"<invoice.category>\",\n'
#     "    \"allowed_amount\": <number or null>,\n"
#     "    \"spent_amount\": <number>,\n"
#     "    \"percent_diff\": <number or null>,\n"
#     '    \"currency\": \"<invoice.currency or policy.currency>\"\n'
#     "  }\n"
#     "}\n"
#     "- All numbers must be numeric types.\n"
#     "- Return ONLY the JSON object. No markdown or analysis outside JSON."
# )


INSTRUCTIONS_VALIDATION = (
    "You are an Expense Policy Validation Agent.\n\n"
    "Your job: Decide how to route an expense claim and return ONLY ONE valid JSON object.\n\n"
    "Inputs are employee, policy, and invoice objects.\n\n"
    "Definitions:\n"
    "- allowed_amount := policy.max_allowance (number) or null if unavailable\n"
    "- spent_amount  := invoice.total_amount (number)\n"
    "- percent_over  := ((spent_amount - allowed_amount) / allowed_amount) * 100, only if allowed_amount > 0; otherwise null\n"
    "- Round percent_over (reported as percent_diff) to 2 decimals\n\n"
    "Case-wise tagging (apply in this order):\n"
    "1) Missing/invalid policy (allowed_amount is null or <= 0):\n"
    "   tag = 'Finance Pending', decision = 'Send to Finance Team'\n"
    "2) If spent_amount <= allowed_amount:\n"
    "   tag = 'Auto Approved', decision = 'Approved'\n"
    "3) If percent_over > 25:\n"
    "   tag = 'Rejected', decision = 'Reject'\n"
    "4) If percent_over > 10 and percent_over < 25:\n"
    "   tag = 'Finance Pending', decision = 'Send to Finance Team'\n"
    "5) If percent_over >= 0 and percent_over <= 10:\n"
    "   tag = 'Pending', decision = 'Send to Manager'\n\n"
    "Output JSON shape:\n"
    "{\n"
    '  \"tag\": \"<Auto Approved | Finance Pending | Pending | Rejected>\",\n'
    '  \"decision\": \"<Approved | Send to Finance Team | Send to Manager | Reject>\",\n'
    '  \"message\": \"<summary mentioning employee name or id, grade, spent vs allowed, reason>\",\n'
    '  \"metrics\": {\n'
    '    \"grade\": \"<employee.grade>\",\n'
    '    \"category\": \"<invoice.category>\",\n'
    "    \"allowed_amount\": <number or null>,\n"
    "    \"spent_amount\": <number>,\n"
    "    \"percent_diff\": <number or null>,\n"
    '    \"currency\": \"<invoice.currency or policy.currency>\"\n'
    "  }\n"
    "}\n\n"
    "- All numeric fields must be numbers (not strings).\n"
    "- Return ONLY the JSON object. No markdown or analysis outside JSON."
)



# =========================================================
# UTILITIES
# =========================================================
# def load_employee_by_email(email: str) -> Optional[Dict[str, Any]]:
#     query = text("SELECT * FROM employees WHERE email = :email;")
#     with engine.connect() as conn:
#         result = conn.execute(query, {"email": email}).mappings().first()
#         return dict(result) if result else None

def image_to_data_url(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def read_pdf_text(pdf_path: str) -> str:
    out = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            out.append(page.get_text("text"))
    return "\n".join(out).strip()

def _to_float(x) -> float:
    if x is None:
        return 0.0
    s = str(x).strip()
    try:
        return float(s)
    except Exception:
        pass
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    try:
        if cleaned in {"", ".", "-", "-.", ".-"}:
            return 0.0
        return float(cleaned)
    except Exception:
        return 0.0

def _parse_date_any(s: str) -> Optional[dt.date]:
    if not s:
        return None
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

def _guess_location_from_text(txt: Optional[str]) -> Optional[str]:
    if not txt:
        return None
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(trigger in low for trigger in ADDRESS_HINT_WORDS):
            block = line
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if not re.search(r"invoice\s*no|gst|pan|bill\s*no|receipt", nxt, re.I):
                    block = block + ", " + nxt
            return block
    m = CITY_HINT_REGEX.search(txt)
    if m:
        city = m.group(1)
        pin = m.group(2)
        if city and pin:
            return f"{city}, {pin}"
        if city:
            return city
    return None

def _safe_vendor(j: Dict[str, Any], filename: Optional[str] = None) -> Optional[str]:
    for k in ["vendor", "merchant", "company", "hotel_name", "restaurant_name", "airline"]:
        if j.get(k):
            return str(j[k])
    for k in ["seller", "vendor", "merchant", "company"]:
        v = j.get(k)
        if isinstance(v, dict):
            for kk in ["name", "hotel_name", "legal_name", "display_name", "brand"]:
                if v.get(kk):
                    return str(v[kk])
            for kk, vv in v.items():
                if isinstance(vv, str) and vv.strip():
                    return vv.strip()
        elif isinstance(v, str) and v.strip():
            return v.strip()
    if filename:
        stem = Path(filename).stem
        if stem:
            guess = stem.split("_")[0] if "_" in stem else stem
            if guess:
                return guess.replace("-", " ").title()
    fname = (j.get("_source_file") or j.get("_file_name") or "").strip()
    if fname:
        stem = Path(fname).stem
        if stem:
            guess = stem.split("_")[0] if "_" in stem else stem
            if guess:
                return guess.replace("-", " ").title()
    return None

def _force_currency_upper(data: Dict[str, Any]):
    if "currency" in data and data["currency"]:
        data["currency"] = str(data["currency"]).upper()

def _normalize_items(items_val: Any, currency_fallback: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(items_val, list):
        for row in items_val:
            if not isinstance(row, dict):
                continue
            desc = row.get("description") or row.get("item") or row.get("service") or "Item"
            amt = _to_float(row.get("amount") or row.get("price") or row.get("total") or 0)
            city = row.get("city") or row.get("location") or None
            cur = row.get("currency") or currency_fallback or "INR"
            out.append(
                {
                    "description": str(desc),
                    "amount": amt,
                    "currency": str(cur).upper(),
                    "city": city,
                }
            )
    return out

def _parse_llm_json(raw: str) -> Dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"LLM did not return valid JSON:\n{raw}")

# =========================================================
# PYDANTIC DATA OBJECTS
# =========================================================
class Seller(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None

class InvoiceItem(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    city: Optional[str] = None

class InvoicePayload(BaseModel):
    invoice_id: str = Field(
        default_factory=lambda: f"INV-{uuid.uuid4().hex[:8].upper()}",
        description="Generated invoice ID if missing"
    )

    employee_id: Optional[str] = None
    expense_date: Optional[dt.date] = None
    currency: Optional[str] = "INR"
    vendor: Optional[str] = None
    category: Optional[str] = None
    total_amount: Optional[float] = 0.0
    items: List[InvoiceItem] = Field(default_factory=list)

    seller: Optional[Seller] = None
    invoice_number: Optional[str] = None
    date: Optional[dt.date] = None

    hotel_name: Optional[str] = None
    check_in: Optional[dt.date] = None
    check_out: Optional[dt.date] = None
    from_location: Optional[str] = Field(default=None, alias="from")
    to_location: Optional[str] = Field(default=None, alias="to")
    booking_number: Optional[str] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    def map_llm_fields(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            return v
        out = dict(v)

        out["employee_id"] = (
            v.get("Employee ID") or v.get("employee_id") or out.get("employee_id")
        )

        if not out.get("invoice_id"):
            maybe_inv = (
                v.get("invoice_number") or v.get("invoice_no")
                or v.get("bill_no") or v.get("receipt_no")
            )
            if maybe_inv:
                out["invoice_id"] = str(maybe_inv)

        if not out.get("invoice_number"):
            out["invoice_number"] = (
                v.get("invoice_number") or v.get("invoice_no")
                or v.get("bill_no") or v.get("receipt_no")
            )

        if not out.get("expense_date"):
            out["expense_date"] = v.get("date") or v.get("invoice_date") or v.get("bill_date")

        if not out.get("currency"):
            out["currency"] = (v.get("currency") or "INR")

        if v.get("total_amount") is not None:
            out["total_amount"] = _to_float(v.get("total_amount"))
        elif v.get("total") is not None:
            out["total_amount"] = _to_float(v.get("total"))
        elif out.get("total_amount") is not None:
            out["total_amount"] = _to_float(out.get("total_amount"))
        else:
            out["total_amount"] = 0.0

        out["category"] = v.get("category") or out.get("category")

        raw_seller = v.get("seller") or out.get("seller") or {}
        if isinstance(raw_seller, dict):
            out["seller"] = {
                "name": raw_seller.get("name"),
                "location": raw_seller.get("location"),
            }
        else:
            out["seller"] = {"name": str(raw_seller), "location": None}

        if not out.get("vendor"):
            if isinstance(out["seller"], dict) and out["seller"].get("name"):
                out["vendor"] = out["seller"]["name"]

        out["hotel_name"] = (
            v.get("hotel_name")
            or (raw_seller.get("hotel_name") if isinstance(raw_seller, dict) else None)
            or out.get("hotel_name")
        )
        out["booking_number"] = v.get("booking_number") or v.get("pnr") or out.get("booking_number")
        out["from_location"] = v.get("from") or v.get("source") or out.get("from_location")
        out["to_location"] = v.get("to") or v.get("destination") or out.get("to_location")
        out["check_in"] = v.get("check_in") or out.get("check_in")
        out["check_out"] = v.get("check_out") or out.get("check_out")

        out["items"] = _normalize_items(
            v.get("items"),
            currency_fallback=out.get("currency", "INR"),
        )

        return out

    @field_validator("expense_date", "date", "check_in", "check_out", mode="before")
    def _coerce_dates(cls, v):
        if v is None:
            return None
        if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
            return v
        if isinstance(v, dt.datetime):
            return v.date()
        try:
            s = str(v).split("T")[0]
            return _parse_date_any(s)
        except Exception:
            return None

    @field_validator("currency")
    def _upper_currency(cls, v):
        return v.upper() if isinstance(v, str) else v

    @field_validator("total_amount")
    def _non_negative_total(cls, v):
        if v is not None and v < 0:
            raise ValueError("total_amount cannot be negative")
        return v

class ExtractionResult(BaseModel):
    payload: InvoicePayload
    raw_text_preview: Optional[str] = None
    ocr_engine: Optional[str] = None

# =========================================================
# VALIDATION
# =========================================================
def _enforce_validation_rules(employee_row, policy_row, invoice_payload_dict) -> Dict[str, Any]:
    """
    Hard, deterministic routing according to the specified rules:
      - If spent <= allowed: Auto Approved / Approved
      - If >25% over: Rejected / Reject
      - If 10%–25% over: Finance Pending / Send to Finance Team
      - If 0%–10% over: Pending / Send to Manager
      - Missing/invalid policy: Finance Pending / Send to Finance Team
    """
    first_name = last_name = grade = manager_id = None
    if employee_row:
        first_name = employee_row.get("first_name")
        last_name = employee_row.get("last_name")
        grade = employee_row.get("grade")
        manager_id = employee_row.get("manager_id")

    emp_display = " ".join([p for p in [first_name, last_name] if p]) or "Employee"
    category = invoice_payload_dict.get("category")
    spent_amount = float(invoice_payload_dict.get("total_amount") or 0.0)
    currency = invoice_payload_dict.get("currency") or (policy_row or {}).get("currency") or "INR"

    # Missing / invalid policy => Finance Pending
    if not policy_row or policy_row.get("max_allowance") is None:
        return {
            "tag": "Finance Pending",
            "decision": "Send to Finance Team",
            "message": (
                f"{emp_display} (Grade {grade}) submitted a {category} expense of "
                f"{currency} {spent_amount:.2f}, but no policy / max allowance was found. "
                "Sending to Finance Team for manual review."
            ),
            "metrics": {
                "grade": grade,
                "category": category,
                "allowed_amount": None,
                "spent_amount": spent_amount,
                "percent_diff": None,
                "currency": currency,
            },
            "manager_id": manager_id,
        }

    allowed_amount = float(policy_row.get("max_allowance") or 0.0)
    if allowed_amount <= 0:
        return {
            "tag": "Finance Pending",
            "decision": "Send to Finance Team",
            "message": (
                f"{emp_display} (Grade {grade}) submitted a {category} expense of "
                f"{currency} {spent_amount:.2f}, but policy limit was invalid. "
                "Sending to Finance Team for manual review."
            ),
            "metrics": {
                "grade": grade,
                "category": category,
                "allowed_amount": None,
                "spent_amount": spent_amount,
                "percent_diff": None,
                "currency": currency,
            },
            "manager_id": manager_id,
        }

    # Compute overage
    if spent_amount <= allowed_amount:
        percent_diff = 0.0
    else:
        percent_diff = ((spent_amount - allowed_amount) / allowed_amount) * 100.0
    pd2 = round(percent_diff, 2)

    # Enforce bands
    if spent_amount <= allowed_amount:
        tag, decision, reason = "Auto Approved", "Approved", "This is within the allowed limit, so it is auto approved."
    elif pd2 <= 10:
        tag, decision, reason = "Pending", "Send to Manager", "Exceeds the policy limit by up to 10%. Send to manager."
    elif pd2 <= 25:
        tag, decision, reason = "Finance Pending", "Send to Finance Team", "Exceeds the policy limit by 10%–25%. Finance review."
    else:
        tag, decision, reason = "Rejected", "Reject", "Exceeds the policy limit by more than 25%. Rejected."

    return {
        "tag": tag,
        "decision": decision,
        "message": (
            f"{emp_display} (Grade {grade}) submitted a {category} expense of "
            f"{currency} {spent_amount:.2f}. Policy allows up to {currency} {allowed_amount:.2f}. {reason}"
        ),
        "metrics": {
            "grade": grade,
            "category": category,
            "allowed_amount": allowed_amount,
            "spent_amount": spent_amount,
            "percent_diff": pd2,
            "currency": currency,
        },
        "manager_id": manager_id,
    }

class ValidationAgent:
    """
    Strict, rule-first validator:
      1) Compute deterministic decision via _enforce_validation_rules()
      2) Optionally ask LLM to write a nicer 'message' ONLY
      3) Add 'rule_band' for UI badges: within_limit | over_by_0_to_10 | over_by_10_to_25 | over_by_25_plus | no_policy
    """
    def __init__(self, llm=None, use_llm_message: bool = True):
        self.llm = llm if llm is not None else llm_json
        self.use_llm_message = bool(use_llm_message and OPENAI_READY)

    @staticmethod
    def _band_from_metrics(metrics: Dict[str, Any]) -> str:
        if not metrics or metrics.get("allowed_amount") in (None, 0):
            return "no_policy"
        pdiff = metrics.get("percent_diff")
        if pdiff is None:
            return "no_policy"
        try:
            pd = float(pdiff)
        except Exception:
            return "no_policy"
        if pd <= 0:
            return "within_limit"
        if pd <= 10:
            return "over_by_0_to_10"
        if pd <= 25:
            return "over_by_10_to_25"
        return "over_by_25_plus"

    def validate(self, employee_row, policy_row, invoice_payload_dict) -> Dict[str, Any]:
        base = _enforce_validation_rules(employee_row, policy_row, invoice_payload_dict)
        base["rule_band"] = self._band_from_metrics(base.get("metrics"))

        if not self.use_llm_message:
            return base

        try:
            msg_prompt = (
                "You are helping write a concise, professional explanation for an expense validation decision.\n"
                "Given EMPLOYEE, POLICY, and INVOICE below, produce ONLY a JSON object like:\n"
                "{ \"message\": \"<one or two sentences explaining the reason and next step>\" }\n"
                "Do NOT include tag/decision/metrics.\n\n"
                f"EMPLOYEE: {json.dumps(employee_row or {}, ensure_ascii=False)}\n"
                f"POLICY: {json.dumps(policy_row or {}, ensure_ascii=False)}\n"
                f"INVOICE: {json.dumps(invoice_payload_dict or {}, ensure_ascii=False)}\n"
                f"DECISION_ALREADY_MADE: {json.dumps({'tag': base.get('tag'), 'decision': base.get('decision')})}\n"
            )
            resp = self.llm.invoke([HumanMessage(content=[{"type": "text", "text": msg_prompt}])])
            raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
            parsed = _parse_llm_json(raw)
            if isinstance(parsed, dict) and parsed.get("message"):
                base["message"] = str(parsed["message"]).strip()
        except Exception:
            pass

        return base

# =========================================================
# EXTRACTION CORE
# =========================================================
def _postprocess_extraction(
    data: Dict[str, Any],
    emp_id: Optional[str],
    filename: Optional[str],
    raw_text: Optional[str],
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data
    if emp_id and not data.get("Employee ID"):
        data["Employee ID"] = emp_id
    _force_currency_upper(data)

    if "total_amount" in data:
        data["total_amount"] = _to_float(data["total_amount"])
    elif "total" in data:
        data["total_amount"] = _to_float(data["total"])
    else:
        data["total_amount"] = 0.0

    seller_block = data.get("seller")
    if not isinstance(seller_block, dict):
        seller_block = {}
    if not seller_block.get("name"):
        vendor_guess = _safe_vendor(data, filename=filename)
        seller_block["name"] = vendor_guess if vendor_guess else None
    if not seller_block.get("location"):
        loc_guess = data.get("location") or data.get("address")
        if not loc_guess and isinstance(data.get("seller"), dict):
            nested = data["seller"]
            for key in ["location", "address", "branch_address", "branch", "city"]:
                if isinstance(nested.get(key), str) and nested.get(key).strip():
                    loc_guess = nested.get(key)
                    break
        if not loc_guess and raw_text:
            loc_guess = _guess_location_from_text(raw_text)
        seller_block["location"] = loc_guess if loc_guess else None
    data["seller"] = seller_block

    for must_key in ["invoice_number", "date", "currency", "category", "items"]:
        if must_key not in data:
            data[must_key] = [] if must_key == "items" else None
    return data

def extract_json_from_image(image_path: str, emp_id_hint: Optional[str]) -> Dict[str, Any]:
    msg = HumanMessage(
        content=[
            {"type": "text", "text": INSTRUCTIONS_IMAGE},
            {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
        ]
    )
    resp = llm_json.invoke([msg])
    raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    parsed = _parse_llm_json(raw)
    parsed["_source_file"] = os.path.basename(image_path)
    return _postprocess_extraction(parsed, emp_id_hint or "UNKNOWN", os.path.basename(image_path), None)

def extract_json_from_pdf(pdf_path: str, emp_id_hint: Optional[str]) -> Dict[str, Any]:
    pdf_text = read_pdf_text(pdf_path)
    msg = HumanMessage(content=[{
        "type": "text",
        "text": f"{INSTRUCTIONS_PDF}\n\n--- BEGIN DOCUMENT TEXT ---\n{pdf_text}\n--- END DOCUMENT TEXT ---",
    }])
    resp = llm_json.invoke([msg])
    raw = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    parsed = _parse_llm_json(raw)
    parsed["_source_file"] = os.path.basename(pdf_path)
    return _postprocess_extraction(parsed, emp_id_hint or "UNKNOWN", os.path.basename(pdf_path), pdf_text)

def save_json_to_dir(data: Dict[str, Any], out_dir: str, base_name: str) -> str:
    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    out_path = out_dir_path / (Path(base_name).stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(out_path)

def extract_file_internal(
    file_path: str,
    emp_id_hint: Optional[str],
    out_dir: str,
    save_json_file: bool
) -> ExtractionResult:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Not found: {file_path}")
    ext = p.suffix.lower()

    if ext in SUPPORTED_PDF:
        raw_dict = extract_json_from_pdf(str(p), emp_id_hint=emp_id_hint)
        ocr_engine = "gpt-4o-mini/pdf"
        raw_text_preview = None
    elif ext in SUPPORTED_IMAGES:
        raw_dict = extract_json_from_image(str(p), emp_id_hint=emp_id_hint)
        ocr_engine = "gpt-4o-mini/image"
        raw_text_preview = None
    else:
        raise ValueError(f"Unsupported file type '{ext}'. Provide PDF or image.")

    if save_json_file:
        save_json_to_dir(raw_dict, out_dir, p.name)

    payload = InvoicePayload(**raw_dict)
    return ExtractionResult(payload=payload, raw_text_preview=raw_text_preview, ocr_engine=ocr_engine)

# =========================================================
# PUBLIC HELPERS (used by FastAPI route)
# =========================================================
def extract_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run file extraction and populate state['extraction'] with a normalized payload.
    Expects: file_path (or image_name), employee_id_hint/emp_id, json_out_dir, save_json_file
    """
    file_path = state.get("file_path") or state.get("image_name")
    if not file_path:
        raise ValueError("extract_node: missing 'file_path' (or 'image_name')")
    emp_id_hint = state.get("employee_id_hint") or state.get("emp_id") or None
    out_dir = state.get("json_out_dir", "output/json_extracts")
    raw_save = state.get("save_json_file", True)
    save_json_file = raw_save if isinstance(raw_save, bool) else str(raw_save).lower() == "true"

    result = extract_file_internal(
        file_path=file_path,
        emp_id_hint=emp_id_hint,
        out_dir=out_dir,
        save_json_file=save_json_file,
    )

    extraction_dict = {
        "payload": result.payload.model_dump(mode="python"),
        "raw_text_preview": result.raw_text_preview,
        "ocr_engine": result.ocr_engine,
    }
    state["process_id"] = f"PROC-{uuid.uuid4().hex[:8].upper()}"
    state["extraction"] = extraction_dict
    return state

def _extract_payload_dict_from_state_extraction(extraction_section: Any) -> Dict[str, Any]:
    if isinstance(extraction_section, dict):
        return extraction_section.get("payload", {}) or {}
    if hasattr(extraction_section, "payload"):
        if hasattr(extraction_section.payload, "model_dump"):
            return extraction_section.payload.model_dump(mode="python")
        if isinstance(extraction_section.payload, dict):
            return extraction_section.payload
    return {}

# def load_policies_df(grade: str) -> pd.DataFrame:
#     query = text("""
#         SELECT *
#         FROM expense_policies
#         WHERE applicable_grades ILIKE :pattern
#         ORDER BY category ASC, max_allowance DESC
#     """)
#     with engine.connect() as conn:
#         return pd.read_sql(query, conn, params={"pattern": f"%{grade}%"})

def _pick_policy_for(
    employee_details_list: List[Dict[str, Any]],
    policies_list: List[Dict[str, Any]],
    category: Optional[str]
) -> Optional[Dict[str, Any]]:
    if not employee_details_list:
        return None
    emp_row = employee_details_list[0]
    grade = emp_row.get("grade")
    if not grade or not category:
        return None

    for pol in policies_list:
        pol_cat = pol.get("category")
        pol_allowed = pol.get("applicable_grades", "")
        if pol_cat and pol_cat.lower() == str(category).lower():
            grades_list = [g.strip() for g in str(pol_allowed).split(",")]
            if grade in grades_list:
                return pol
    for pol in policies_list:
        if (pol.get("category") or "").lower() == str(category).lower():
            return pol
    return None

def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    extraction = state.get("extraction")
    if not extraction:
        raise ValueError("No extraction payload found in state. Run extract_node first.")

    payload_dict = _extract_payload_dict_from_state_extraction(extraction)
    emp_id = payload_dict.get("employee_id")
    if not emp_id:
        raise ValueError("Extraction payload missing employee_id; cannot validate.")

    employee_details_list = db_utils.get_employee_details(emp_id)
    employee_row = employee_details_list[0] if employee_details_list else None

    emp_grade = employee_row.get("grade") if employee_row else None
    policies_df = db_utils.load_policies_df(emp_grade) if emp_grade else pd.DataFrame()
    policies_list = policies_df.to_dict("records")
    policy_row = _pick_policy_for(employee_details_list, policies_list, payload_dict.get("category"))


    print("emp grade:",emp_grade)
    print("policies df", policies_df)
    print("policies list", policies_list)
    print("policy row", policy_row)

    validator = ValidationAgent()
    validation_result = validator.validate(employee_row, policy_row, payload_dict)

    state["validation"] = validation_result
    state["tag"] = validation_result.get("tag")
    state["decision"] = validation_result.get("decision")
    return state

def payload_to_json_ready(payload_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce a python-mode payload dict into JSON-safe (dates → ISO)."""
    return InvoicePayload(**payload_dict).model_dump(mode="json")

def run_full(state: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience: extract then validate."""
    state = extract_node(state)
    state = validate_node(state)
    return state



# ======= Finance agent ============

# finance_agent.py
import os
import json
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from db import get_connection, safe_query

load_dotenv()

# -------------------------------------------------------------------
# Utility: Execute a SQL and return a DataFrame
# -------------------------------------------------------------------
def fetch_df(sql, params=None):
    with get_connection() as conn:
        rows = safe_query(conn, sql, params)
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

import json
import re

def safe_json_parse(text: str):
    """
    Safely parse possibly messy AI/LLM JSON output into a dict.
    Works even if the string has extra whitespace, text before/after the JSON,
    or multiple JSON objects.
    """
    if not text or not isinstance(text, str):
        print("⚠️ No text to parse")
        return {}

    # Trim whitespace/newlines
    cleaned = text.strip()

    # Try normal parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass  # fallback below

    # Extract the first valid {...} JSON block using regex
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decoding error: {e}")
            print("⚠️ Raw candidate start:", repr(candidate[:200]))
            return {}
    else:
        print("⚠️ Could not find a valid JSON object in text")
        print("Raw preview:", repr(cleaned[:200]))
        return {}

def ensure_list(value, split_on="."):
    if isinstance(value, str):
        return [v.strip() for v in value.split(split_on) if v.strip()]
    if isinstance(value, list):
        return value
    return []


# -------------------------------------------------------------------
# Main Finance AI Agent
# -------------------------------------------------------------------
def run_finance_agent(start_date: date = None, end_date: date = None):
    """
    Queries the finance database, summarizes key insights,
    and uses GPT to generate a business summary and recommendations.
    """

    # ----------------------------------------------------------------
    # 1. Prepare Date Filters
    # ----------------------------------------------------------------
    sql_filter = ""
    params = []
    if start_date and end_date:
        sql_filter = "WHERE claim_date BETWEEN %s AND %s"
        params = [start_date, end_date]

    # ----------------------------------------------------------------
    # 2. Run Core Queries
    # ----------------------------------------------------------------
    summary_sql = f"""
        SELECT 
            COUNT(*) AS total_claims,
            COALESCE(SUM(amount), 0)::float AS total_spend,
            AVG(amount)::float AS avg_claim_amount,
            AVG(CASE WHEN auto_approved THEN 1 ELSE 0 END)::float AS auto_approval_rate
        FROM expense_claims
        {sql_filter};
    """
    df_summary = fetch_df(summary_sql, params)



    
    records_sql = f"""
        SELECT 
            c.claim_id,
            c.employee_id,
            (e.first_name || ' ' || e.last_name) AS employee_name,
            c.claim_date,
            c.expense_category,
            c.amount::float,
            c.currency,
            c.vendor_name,
            c.payment_mode,
            c.status,
            c.auto_approved,
            c.is_duplicate,
            c.fraud_flag,
            c.details,
            p.max_allowance::float AS policy_limit,
            CASE 
                WHEN c.amount > p.max_allowance THEN TRUE 
                ELSE FALSE 
            END AS over_limit_flag
        FROM expense_claims c
        JOIN employees e ON c.employee_id = e.employee_id
        LEFT JOIN expense_policies p ON c.expense_category = p.category
        WHERE c.claim_date BETWEEN %s AND %s
        ORDER BY c.claim_date DESC;
    """

    params = [start_date, end_date]
    df_claims = fetch_df(records_sql, params)



    top_categories_sql = f"""
        SELECT expense_category, SUM(amount)::float AS total_spend
        FROM expense_claims
        {sql_filter}
        GROUP BY expense_category
        ORDER BY total_spend DESC
        LIMIT 5;
    """
    df_cats = fetch_df(top_categories_sql, params)

    top_vendors_sql = f"""
        SELECT vendor_name, SUM(amount)::float AS total_spend
        FROM expense_claims
        {sql_filter}
        GROUP BY vendor_name
        ORDER BY total_spend DESC
        LIMIT 5;
    """
    df_vendors = fetch_df(top_vendors_sql, params)

    policy_violations_sql = f"""
        SELECT 
            (e.first_name || ' ' || e.last_name) AS employee_name,
            c.expense_category,
            c.amount::float,
            p.max_allowance::float AS policy_limit
        FROM expense_claims c
        JOIN employees e ON c.employee_id = e.employee_id
        JOIN expense_policies p ON c.expense_category = p.category
        WHERE claim_date BETWEEN %s AND %s
        AND c.amount > p.max_allowance;
    """






    df_violations = fetch_df(policy_violations_sql, params)

    # ----------------------------------------------------------------
    # 3. Build Summary Data
    # ----------------------------------------------------------------
    key_metrics = df_summary.iloc[0].to_dict() if not df_summary.empty else {
        "total_claims": 0,
        "total_spend": 0.0,
        "avg_claim_amount": 0.0,
        "auto_approval_rate": 0.0,
    }

    insights = []
    if not df_cats.empty:
        top_cat = df_cats.iloc[0]
        insights.append(f"Highest spend category: {top_cat['expense_category']} (₹{top_cat['total_spend']:,.0f}).")

    if not df_vendors.empty:
        top_vendor = df_vendors.iloc[0]
        insights.append(f"Top vendor: {top_vendor['vendor_name']} (₹{top_vendor['total_spend']:,.0f}).")

    if not df_violations.empty:
        insights.append(f"{len(df_violations)} claims exceeded their policy limits.")

    # if key_metrics["fraud_flags"] > 0:
    #     insights.append(f"{key_metrics['fraud_flags']} claims flagged as potential frauds.")

    # if key_metrics["duplicates"] > 0:
    #     insights.append(f"{key_metrics['duplicates']} duplicate claims detected.")

    policy_optimizations = []
    if not df_violations.empty:
        policy_optimizations.append("Revisit category spending limits in expense_policies for high-frequency violations.")
    if key_metrics["auto_approval_rate"] < 0.3:
        policy_optimizations.append("Increase automation thresholds to improve auto-approval efficiency.")
    # if key_metrics["fraud_flags"] > 0:
    #     policy_optimizations.append("Tighten fraud detection rules for flagged vendors or employees.")

    risk_alerts = []
    if not df_violations.empty:
        risk_alerts.append(f"{len(df_violations)} employees exceeded expense caps.")
    # if key_metrics["fraud_flags"] > 0:
    #     risk_alerts.append("Fraud detection triggered — review flagged claims immediately.")

    # ----------------------------------------------------------------
    # 4. Optional: Generate Executive Summary using GPT
    # ----------------------------------------------------------------
    executive_summary = "Finance data analyzed successfully."
    try:

        System_prompt="""
    You are an autonomous Finance Intelligence Agent with full SQL querying capabilities.
    You are connected to a PostgreSQL database named agent_max containing these tables:

    - employees(employee_id, employee_name, department, designation)
    - expense_claims(id, claim_id, employee_id, claim_date, expense_category, amount, currency, vendor_name, payment_mode, status, auto_approved, is_duplicate, fraud_flag, details)
    - expense_policies(policy_id, expense_category, max_limit, approval_required, allowed_payment_modes)
    - vendors(vendor_id, vendor_name, risk_score, last_transaction_date)
    - reimbursement_accounts(...)
    - per_diem_rates(...)
    - expense_validation_logs(...)

    Your task is to:
    1. Generate SQL queries to summarize key financial metrics.
    2. Detect anomalies (e.g.,Reoccuring claims, highest cliaming employee, over-limit expenses).
    3. Identify top departments, vendors, and categories by spend.
    4. Recommend policy optimizations.
    5. Output **structured JSON** insights ready for the Streamlit dashboard.
    6. Recommend Claim decisions

    Your JSON output **must** follow this schema:

    {
    "executive_summary": {
        "Summary":"string", 
        "actions":"string",
        "recommended_claim_decisions":"string"
    },
    "key_metrics": {
        "total_claims": int,
        "total_spend": float,
        "avg_claim_amount": float,
        "auto_approval_rate": float,
    },
    "insights": ["string", "..."],
    "policy_optimizations": ["string", "..."],
    "risk_alerts": ["string", "..."],
    "actions": ["string", "..."],
    }
    """


        client = OpenAI()
        prompt = f"""
        You are a corporate finance analytics assistant.
        Based on the following data, generate a concise summary for a CFO dashboard. 
        Analyse the data and generate potential actions and Risks.

        Key Metrics:
        {json.dumps(key_metrics, indent=2)}

        Insights:
        {json.dumps(insights, indent=2)}

        Policy Violations:
        {len(df_violations)}

        Top Vendors:
        {json.dumps(df_vendors.to_dict(orient='records'), indent=2)}

        All Claims:
        {json.dumps(df_claims.to_dict(orient='records'), indent=2, default=str)}
        """

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": System_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        executive_summary = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ GPT summary generation failed: {e}")

    
    # ----------------------------------------------------------------
    # 5. Build Final JSON Result
    # ----------------------------------------------------------------
    # import json
    print(type(executive_summary))
    print(executive_summary)

    executive_summary_json = safe_json_parse(executive_summary)

    # # Safely extract and split actions
    
    print(executive_summary_json)
    # actions_field = executive_summary_json['executive_summary']["actions"]
    print(executive_summary_json['executive_summary'])
    exec_summary=executive_summary_json['executive_summary']


    # Construct final result
    result = {
        "executive_summary": exec_summary.get("Summary", ""),
        "key_metrics": key_metrics,
        "insights": insights,
        "policy_optimizations": policy_optimizations,
        "risk_alerts": risk_alerts,
        "actions": ensure_list(exec_summary.get("actions")),
        "recommended_claim_decisions": ensure_list(exec_summary.get("recommended_claim_decisions")),
    }


    print("result: ",result)

    return result
