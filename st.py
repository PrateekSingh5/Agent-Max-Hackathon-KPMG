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
    - Step 2 (Review): user edits the form
    - Step 3 (Validate): POST /api/Agent?phase=validate with final JSON in body
    """
    st.subheader("🧠 Extractor Node — Extract data from image/PDF")

    # ----- Controls -----
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
        st.session_state.item_count = 1
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
            # Send as JSON body (server can also accept via query, but JSON is more robust)
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

    # If not in "form" phase yet
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

    # Optional: gate by category (example currently expects hotel)
    if payload.get("category") != "hotel":
        st.info(f"Form available only for category 'hotel'. Found: {payload.get('category')!r}")
        return

    # Ensure item counter
    if "item_count" not in st.session_state:
        st.session_state.item_count = max(1, len(payload.get("items", [])))

    # ---------- FORM ----------
    with st.form(key="invoice_form", clear_on_submit=False):
        st.subheader("Top-level fields")
        c1, c2 = st.columns(2)
        with c1:
            invoice_id = st.text_input("invoice_id", value=payload.get("invoice_id", ""))
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
            expense_date = st.date_input("expense_date", value=parse_iso_date(payload.get("expense_date", to_iso(date.today()))))
            vendor = st.text_input("vendor", value=payload.get("vendor", ""))
            currency = st.text_input("currency", value=payload.get("currency", "INR"))
        with c2:
            invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
            inv_date = st.date_input("date", value=parse_iso_date(payload.get("date", to_iso(date.today()))))
            total_amount = st.number_input("total_amount", value=float(payload.get("total_amount", 0.0) or 0.0), step=1.0, min_value=0.0)
            total = st.number_input("total", value=float(payload.get("total", 0.0) or 0.0), step=1.0, min_value=0.0)
            category = st.text_input("category", value=payload.get("category", "hotel"))

        st.markdown("---")
        st.subheader("Buyer")
        b1, b2 = st.columns(2)
        with b1:
            buyer_name = st.text_input("buyer.name", value=deep_get(payload, "buyer.name", ""))
        with b2:
            buyer_email = st.text_input("buyer.email", value=deep_get(payload, "buyer.email", ""))

        st.subheader("Seller")
        s1, s2 = st.columns(2)
        with s1:
            seller_hotel = st.text_input("seller.hotel_name", value=deep_get(payload, "seller.hotel_name", ""))
        with s2:
            seller_location = st.text_input("seller.location", value=deep_get(payload, "seller.location", "") or "")

        st.markdown("---")
        st.subheader("Booking Details")
        bd1, bd2 = st.columns(2)
        with bd1:
            booking_number = st.text_input("booking_details.booking_number", value=deep_get(payload, "booking_details.booking_number", ""))
            check_in = st.date_input("booking_details.check_in", value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today()))))
        with bd2:
            payment_reference = st.text_input("booking_details.payment_reference", value=deep_get(payload, "booking_details.payment_reference", ""))
            check_out = st.date_input("booking_details.check_out", value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today()))))

        st.markdown("---")
        st.subheader("Items")
        st.caption("Adjust the count, then edit each row below.")
        st.session_state.item_count = st.number_input(
            "Number of items",
            min_value=1,
            max_value=50,
            value=max(1, st.session_state.item_count),
            step=1
        )

        items_src = payload.get("items", [])
        items = []
        for i in range(int(st.session_state.item_count)):
            st.write(f"**Item #{i+1}**")
            dflt = items_src[i] if (isinstance(items_src, list) and i < len(items_src)) else {
                "description": "",
                "category": "",
                "amount": 0.0,
                "currency": currency,
                "merchant": "",
                "city": ""
            }
            ic1, ic2, ic3 = st.columns([2, 1, 1])
            with ic1:
                desc = st.text_input(f"items[{i}].description", value=dflt.get("description", ""), key=f"desc_{i}")
            with ic2:
                cat = st.text_input(f"items[{i}].category", value=dflt.get("category", ""), key=f"cat_{i}")
            with ic3:
                amt = st.number_input(f"items[{i}].amount", value=float(dflt.get("amount", 0.0) or 0.0), step=1.0, min_value=0.0, key=f"amt_{i}")

            ic4, ic5, ic6 = st.columns([1, 1, 1])
            with ic4:
                icur = st.text_input(f"items[{i}].currency", value=dflt.get("currency", currency), key=f"cur_{i}")
            with ic5:
                merch = st.text_input(f"items[{i}].merchant", value=dflt.get("merchant", ""), key=f"merch_{i}")
            with ic6:
                city = st.text_input(f"items[{i}].city", value=(dflt.get("city") or ""), key=f"city_{i}")

            items.append({
                "description": desc,
                "category": cat,
                "amount": float(amt),
                "currency": icur,
                "merchant": merch,
                "city": city if city.strip() else None
            })
            st.divider()

        submitted = st.form_submit_button("Submit")

    # ----- After form submit: keep last payload and validate math -----
    if submitted:
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

        items_sum = round(sum(x.get("amount", 0.0) for x in items), 2)
        warn_msgs = []
        if abs(items_sum - payload_out["total"]) > 0.01:
            warn_msgs.append(f"Sum(items.amount) = {items_sum} ≠ total = {payload_out['total']}")
        if abs(items_sum - payload_out["total_amount"]) > 0.01:
            warn_msgs.append(f"Sum(items.amount) = {items_sum} ≠ total_amount = {payload_out['total_amount']}")

        if warn_msgs:
            st.warning("⚠️ Validation checks:\n- " + "\n- ".join(warn_msgs))
        else:
            st.success("✅ Validation passed (items sum matches totals).")

    # ----- Show current JSON + Validate button -----
    if st.session_state.last_payload:
        st.subheader("Resulting JSON")
        st.json(st.session_state.last_payload)

        st.markdown("---")
        st.subheader("⚙️ Validate the Final JSON (after your review)")
        if st.button("✅ Submit & Validate", key="run_agent_validate", use_container_width=True):
            with st.spinner("Validating edited payload..."):
                try:
                    # send phase in query, payload in JSON body
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

st.markdown("---")

# ----------------------------
# Router
# ----------------------------
if st.session_state.authenticated:
    user_name = st.session_state.user_details.get('name', 'User')
    user_role = st.session_state.user_details.get('role', 'User')

    st.header(f"Welcome back, {user_name}! 👋")

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
