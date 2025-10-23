# st.py

import os
import re
import json
import time
from pathlib import Path
from datetime import date, datetime

import requests
import streamlit as st
import agent as _agent  # your module

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="AgentMax – Extractor", layout="wide")

# ----------------------------
# Config
# ----------------------------
BASE_API = "http://localhost:8000"
OUTPUT_DIR = "output/langchain_json"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

input_dir = Path("./input/images")
input_dir.mkdir(parents=True, exist_ok=True)

AGENT_ENDPOINT = f"{BASE_API}/api/Agent"   # unified endpoint

# ----------------------------
# Helpers
# ----------------------------
def parse_iso_date(s: str) -> date:
    """Parse YYYY-MM-DD; fallback to today on error."""
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return date.today()

def to_iso(d: date | str | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, str):
        return d  # assume already ISO
    return d.isoformat()

def deep_get(d, path, default=None):
    """Safely get a nested key: deep_get(resp, 'extraction.payload.seller.hotel_name', '')"""
    cur = d or {}
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

# ----------------------------
# UI: Extractor Node (Human-in-the-loop)
# ----------------------------
def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
    """
    Human-in-the-loop Extractor + Validator UI
    - Step 1 (Extract): POST /api/Agent (json={"phase":"extract", ...}) -> prefill form
    - Step 2 (Review): user edits the form (NO item-level edits)
    - Step 3 (Validate): POST /api/Agent?phase=validate with final JSON in body
    """
    uploaded_file = st.file_uploader(
        "Upload invoice/receipt (PNG/JPG/JPEG/WEBP/PDF)",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        accept_multiple_files=False,
        key="uploader_invoice_image",
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        run_clicked = st.button("Click to Review", use_container_width=True, key="run_extractor_btn")
    with c2:
        reset_clicked = st.button("Reset", use_container_width=True, key="reset_extractor_btn")

    # ----- Reset flow -----
    if reset_clicked:
        st.session_state.ui_step = "idle"
        st.session_state.extraction_resp = None
        st.session_state.extracted_payload = None
        st.session_state.uploaded_image_path = None
        st.session_state.last_payload = None
        st.success("Extractor state cleared.")
        return

    # ----- On Extract -----
    if run_clicked:
        if not emp_id:
            st.warning("Please enter Employee ID (login first).")
            return
        if not uploaded_file:
            st.warning("Please upload an image/PDF file.")
            return

        # Save file locally so FastAPI can read it
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", uploaded_file.name)
        file_path = input_dir / safe_name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            req_body = {
                "phase": "extract",
                "image_name": str(file_path),
                "emp_id": emp_id,
                "json_out_dir": output_dir,
                "save_json_file": True,
            }
            r = requests.post(AGENT_ENDPOINT, json=req_body, timeout=120)
            if r.status_code != 200:
                st.error(f"API error {r.status_code}: {r.text}")
                return

            resp = r.json() or {}
            payload = deep_get(resp, "extraction.payload", {}) or {}

            st.session_state.uploaded_image_path = str(file_path)
            st.session_state.extraction_resp = resp
            st.session_state.extracted_payload = payload
            st.session_state.ui_step = "form"

            st.success("Extraction complete (phase=extract) ✅")
            st.write("**Saved at:**", str(file_path))

        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {e}")
            return

    if st.session_state.ui_step != "form":
        st.info("Upload a file and click **Click to Review** to continue.")
        return

    # ----- Render form from payload -----
    payload = st.session_state.extracted_payload or {}
    file_path = st.session_state.uploaded_image_path

    if not isinstance(payload, dict) or not payload:
        st.warning("No payload returned from API.")
        if st.session_state.extraction_resp:
            with st.expander("Raw API response"):
                st.json(st.session_state.extraction_resp)
        return

    with st.expander("Raw extraction payload"):
        st.json(payload)

    # Optional: gate by category
    if payload.get("category") != "hotel":
        st.info(f"Form available only for category 'hotel'. Found: {payload.get('category')!r}")
        return

    # ---------- FORM (NO item-level fields) ----------
    with st.form(key="invoice_form", clear_on_submit=False):
        st.write("**Top-level fields**")
        c = st.columns(5)
        with c[0]:
            invoice_id = st.text_input("invoice_id", value=payload.get("invoice_id", ""))
        with c[1]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[2]:
            expense_date = st.date_input("expense_date", value=parse_iso_date(payload.get("expense_date", to_iso(date.today()))))
        with c[3]:
            vendor = st.text_input("vendor", value=payload.get("vendor", ""))
        with c[4]:
            currency = st.text_input("currency", value=payload.get("currency", "INR"))

        c = st.columns(5)
        with c[0]:
            invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
        with c[1]:
            inv_date = st.date_input("date", value=parse_iso_date(payload.get("date", to_iso(date.today()))))
        with c[2]:
            total_amount = st.number_input("total_amount", value=float(payload.get("total_amount", 0.0) or 0.0), step=1.0, min_value=0.0)
        with c[3]:
            total = st.number_input("total", value=float(payload.get("total", 0.0) or 0.0), step=1.0, min_value=0.0)
        with c[4]:
            category = st.text_input("category", value=payload.get("category", "hotel"))

        st.markdown("---")
        st.write("**Buyer**")
        c = st.columns(5)
        with c[0]:
            buyer_name = st.text_input("buyer.name", value=deep_get(payload, "buyer.name", ""))
        with c[1]:
            buyer_email = st.text_input("buyer.email", value=deep_get(payload, "buyer.email", ""))
        # c[2], c[3], c[4] left intentionally unused for consistent 5-col layout

        st.write("**Seller**")
        c = st.columns(5)
        with c[0]:
            seller_hotel = st.text_input("seller.hotel_name", value=deep_get(payload, "seller.hotel_name", ""))
        with c[1]:
            seller_location = st.text_input("seller.location", value=deep_get(payload, "seller.location", "") or "")
        # c[2], c[3], c[4] unused

        st.markdown("---")
        st.write("**Booking Details**")
        c = st.columns(5)
        with c[0]:
            booking_number = st.text_input("booking_details.booking_number", value=deep_get(payload, "booking_details.booking_number", ""))
        with c[1]:
            payment_reference = st.text_input("booking_details.payment_reference", value=deep_get(payload, "booking_details.payment_reference", ""))
        with c[2]:
            check_in = st.date_input("booking_details.check_in", value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today()))))
        with c[3]:
            check_out = st.date_input("booking_details.check_out", value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today()))))
        # c[4] unused

        submitted = st.form_submit_button("Submit")

    # ----- After form submit: keep items unchanged & simple confirmation -----
    if submitted:
        # Keep items read-only (as returned by API)
        items = payload.get("items", [])

        payload_out = {
            "invoice_id": invoice_id,
            "employee_id": employee_id or emp_id,
            "expense_date": to_iso(expense_date),
            "vendor": vendor,
            "total_amount": round(float(total_amount), 2),
            "currency": currency,
            "items": items,  # unchanged
            "invoice_number": invoice_number,
            "date": to_iso(inv_date),
            "seller": {
                "hotel_name": seller_hotel,
                "location": seller_location if (seller_location or "").strip() else None
            },
            "buyer": {
                "name": buyer_name,
                "email": buyer_email
            },
            "booking_details": {
                "booking_number": booking_number,
                "payment_reference": payment_reference,
                "check_in": to_iso(check_in),
                "check_out": to_iso(check_out)
            },
            "total": round(float(total), 2),
            "category": category or "hotel"
        }
        st.session_state.last_payload = payload_out
        st.session_state.ui_step = "form"
        st.success("Form saved. Items remain unchanged (read-only).")




        from db_utils import save_expense_claim
        items = payload.get("items", [])
        payload_out = {
            "invoice_id": invoice_id,
            "employee_id": employee_id or emp_id,
            "expense_date": to_iso(expense_date),
            "vendor": vendor,
            "total_amount": round(float(total_amount), 2),
            "currency": currency,
            "items": items,
            "invoice_number": invoice_number,
            "date": to_iso(inv_date),
            "seller": {"hotel_name": seller_hotel, "location": seller_location or None},
            "buyer": {"name": buyer_name, "email": buyer_email},
            "booking_details": {
                "booking_number": booking_number,
                "payment_reference": payment_reference,
                "check_in": to_iso(check_in),
                "check_out": to_iso(check_out)
            },
            "total": round(float(total), 2),
            "category": category or "hotel"
        }

        st.session_state.last_payload = payload_out
        st.session_state.ui_step = "form"

        try:
            claim_id = save_expense_claim(payload_out)
            st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
        except Exception as e:
            st.error(f"❌ Database insert failed: {e}")





    # ----- Read-only items view (optional) -----
    if isinstance(payload.get("items", None), list):
        with st.expander("View extracted items (read-only)"):
            st.json(payload["items"])

    # ----- Validate button (Resulting JSON is hidden per request) -----
    if st.session_state.last_payload:
        st.markdown("---")
        st.write("**⚙️ Validate the Final JSON (after your review)**")
        if st.button("✅ Submit & Validate", key="run_agent_validate", use_container_width=True):
            with st.spinner("Validating edited payload..."):
                try:
                    resp = requests.post(
                        AGENT_ENDPOINT,
                        params={"phase": "validate"},
                        json=st.session_state.last_payload,
                        timeout=120
                    )
                    st.write(f"**Status:** {resp.status_code}")
                    try:
                        st.json(resp.json())
                    except ValueError:
                        st.code(resp.text)
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {e}")

# ----------------------------
# Dashboard
# ----------------------------
def dashboard(emp_id: str, output_dir: str, input_dir: Path):
    st.divider()
    extractor_node_ui(emp_id, output_dir, input_dir)
    st.divider()

# ----------------------------
# Session state init
# ----------------------------
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_details' not in st.session_state:
    st.session_state.user_details = {}
if 'emp_id' not in st.session_state:
    st.session_state.emp_id = None
if 'grade' not in st.session_state:
    st.session_state.grade = None
if 'manager_id' not in st.session_state:
    st.session_state.manager_id = None
if 'first_name' not in st.session_state:
    st.session_state.first_name = None

# --- UI flow/session data for extractor ---
if 'ui_step' not in st.session_state:
    st.session_state.ui_step = "idle"   # "idle" | "form"
if 'extraction_resp' not in st.session_state:
    st.session_state.extraction_resp = None
if 'extracted_payload' not in st.session_state:
    st.session_state.extracted_payload = None
if 'uploaded_image_path' not in st.session_state:
    st.session_state.uploaded_image_path = None
if 'last_payload' not in st.session_state:
    st.session_state.last_payload = None
if 'login_error' not in st.session_state:
    st.session_state.login_error = None

# ----------------------------
# Auth helpers
# ----------------------------
def check_credentials(username: str, password: str) -> bool:
    rec = _agent.load_employee_by_email(username)
    if not rec:
        return False
    return password == "password"  # replace with a real check

def get_user_details(username: str):
    return _agent.load_employee_by_email(username)

def login_callback(username, password):
    if check_credentials(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.user_details = {
            "name": (username.split("@")[0]).capitalize() if "@" in username else username.capitalize(),
            "role": "Admin" if username == "admin" else "User",
            "last_login": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        st.session_state.login_error = None
        st.rerun()
    else:
        st.session_state.authenticated = False
        st.session_state.login_error = "Invalid Username or Password. Please try again."

def logout_callback():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_details = {}
    st.rerun()

# ----------------------------
# Sidebar (when logged in)
# ----------------------------
if st.session_state.authenticated:
    with st.sidebar:
        st.write(f"**Signed in as:** {st.session_state.username} 🧑‍💻")
        st.button("Logout", on_click=logout_callback, key="logout_sidebar_btn")

# ----------------------------
# Router
# ----------------------------
if st.session_state.authenticated:
    user_name = st.session_state.user_details.get('name', 'User')
    user_role = st.session_state.user_details.get('role', 'User')

    st.subheader(f"Welcome back, {user_name}! 👋")

    details = get_user_details(st.session_state.username)
    if details:
        st.session_state.emp_id = details.get('employee_id')
        st.session_state.grade = details.get('grade')
        st.session_state.manager_id = details.get('manager_id')
        st.session_state.first_name = details.get('first_name')

    dashboard(st.session_state.emp_id, OUTPUT_DIR, input_dir)

else:
    st.error("🔒 Session Expired or Not Logged In. Please sign in to continue.")

    # Center the login form using columns
    col_empty, col_form, col_empty2 = st.columns([1, 2, 1])

    with col_form:
        with st.form(key="login_form"):
            st.subheader("User Login")
            username = st.text_input("Email:", key="login_username")
            password = st.text_input("Password:", type="password", key="login_password")

            submitted_login = st.form_submit_button("Sign In", use_container_width=True)

            if submitted_login:
                login_callback(username, password)
                if st.session_state.authenticated:
                    st.rerun()
                elif st.session_state.login_error:
                    st.error(st.session_state.login_error)
