import os
import re
import json
import time
from pathlib import Path
from datetime import date, datetime

import requests
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st

import agent as _agent            # your module
from db_utils import save_expense_claim  # writes to DB
from claims_dashboard import load_recent_claims  # import your loader
import db_utils 

# -------------------------------------------------
# PAGE CONFIG (must be first Streamlit call)
# -------------------------------------------------
st.set_page_config(page_title="Employee Dashboard", layout="wide")

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------
BASE_API = "http://localhost:8000"
AGENT_ENDPOINT = f"{BASE_API}/api/Agent"

OUTPUT_DIR = "output/langchain_json"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

input_dir = Path("./input/images")
input_dir.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# SESSION ENFORCERS AND NAV HELPERS
# -------------------------------------------------
def do_logout_and_return():
    # mirror logout in test_portal_login.py
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.access_label = None
    st.session_state.allowed_views = []
    st.switch_page("test_portal_login.py")

def go_manager():
    st.switch_page("pages/manager_dashboard.py")

def go_finance():
    st.switch_page("pages/finance_dashboard.py")

def ensure_employee_allowed():
    """
    Must be logged in AND have access_label in {"E","M"}.
    Otherwise redirect or stop.
    """
    if not st.session_state.get("logged_in", False):
        st.error("Please login first.")
        if st.button("Go to Login"):
            st.switch_page("test_portal_login.py")
        st.stop()

    access_label = st.session_state.get("access_label", "")
    if access_label not in {"E", "M"}:
        st.error("Access denied. Employee portal only.")
        st.sidebar.button("Logout", on_click=do_logout_and_return)
        st.stop()

# -------------------------------------------------
# SMALL HELPERS
# -------------------------------------------------
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
    """Safely get a nested key by dotted path."""
    cur = d or {}
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

# -------------------------------------------------
# CLAIMS DASHBOARD (for this employee only)
# -------------------------------------------------
def show_claims_dashboard():
    st.header("💼 My Expense Claims")
    st.caption("Showing your most recent claims")

    employee_id = st.session_state.get("emp_id")
    if not employee_id:
        st.warning("⚠️ Missing employee_id in session.")
        return

    try:
        df = load_recent_claims(employee_id, 50)
        if df.empty:
            st.info("You have not submitted any claims yet.")
        else:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "claim_id": "Claim ID",
                    "user_name": "Employee Name",
                    "claim_type": "Claim Type",
                    "amount": st.column_config.NumberColumn(format="₹ %.2f"),
                    "currency": "Currency",
                    "status": "Status",
                    "vendor_name": "Vendor",
                    "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
                },
            )
    except Exception as e:
        st.error(f"Failed to load claims: {e}")

# -------------------------------------------------
# EXTRACTOR NODE UI
# -------------------------------------------------
def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
    """
    Step 1 (Extract): POST /api/Agent with phase='extract' → get payload
    Step 2 (Review): user edits top-level form (NOT line items)
    Step 3 (Validate): POST /api/Agent?phase=validate → send final JSON
    """
    st.header("📤 Upload & Review Bill")

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

    # Reset flow
    if reset_clicked:
        st.session_state.ui_step = "idle"
        st.session_state.extraction_resp = None
        st.session_state.extracted_payload = None
        st.session_state.uploaded_image_path = None
        st.session_state.last_payload = None
        st.success("Extractor state cleared.")
        return

    # Run extraction
    if run_clicked:
        if not emp_id:
            st.warning("Please log in again: no emp_id in session.")
            return
        if not uploaded_file:
            st.warning("Please upload an image/PDF file first.")
            return

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

            st.success("Extraction complete ✅")
            st.write("**Saved at:**", str(file_path))

        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {e}")
            return

    # If we're not in 'form' mode yet, stop here
    if st.session_state.ui_step != "form":
        st.info("Upload a file and click **Click to Review** to continue.")
        return

    # Render editable form
    payload = st.session_state.extracted_payload or {}

    if not isinstance(payload, dict) or not payload:
        st.warning("No payload returned from API.")
        if st.session_state.extraction_resp:
            with st.expander("Raw API response"):
                st.json(st.session_state.extraction_resp)
        return

    with st.expander("Raw extraction payload"):
        st.json(payload)

    # Gate by category if you only want 'hotel' invoices editable
    if payload.get("category") != "hotel":
        st.info(f"Form available only for category 'hotel'. Found: {payload.get('category')!r}")
        return

    # Editable top-level form (no item-level edits)
    with st.form(key="invoice_form", clear_on_submit=False):
        st.write("**Top-level fields**")
        c = st.columns(5)
        with c[0]:
            invoice_id = st.text_input("invoice_id", value=payload.get("invoice_id", ""))
        with c[1]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[2]:
            expense_date = st.date_input(
                "expense_date",
                value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
            )
        with c[3]:
            vendor = st.text_input("vendor", value=payload.get("vendor", ""))
        with c[4]:
            currency = st.text_input("currency", value=payload.get("currency", "INR"))

        c = st.columns(5)
        with c[0]:
            invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
        with c[1]:
            inv_date = st.date_input(
                "date",
                value=parse_iso_date(payload.get("date", to_iso(date.today())))
            )
        with c[2]:
            total_amount = st.number_input(
                "total_amount",
                value=float(payload.get("total_amount", 0.0) or 0.0),
                step=1.0,
                min_value=0.0
            )
        with c[3]:
            total = st.number_input(
                "total",
                value=float(payload.get("total", 0.0) or 0.0),
                step=1.0,
                min_value=0.0
            )
        with c[4]:
            category = st.text_input("category", value=payload.get("category", "hotel"))

        st.markdown("---")
        st.write("**Buyer**")
        c = st.columns(5)
        with c[0]:
            buyer_name = st.text_input("buyer.name", value=deep_get(payload, "buyer.name", ""))
        with c[1]:
            buyer_email = st.text_input("buyer.email", value=deep_get(payload, "buyer.email", ""))

        st.write("**Seller**")
        c = st.columns(5)
        with c[0]:
            seller_hotel = st.text_input("seller.hotel_name", value=deep_get(payload, "seller.hotel_name", ""))
        with c[1]:
            seller_location = st.text_input("seller.location", value=deep_get(payload, "seller.location", "") or "")

        st.markdown("---")
        st.write("**Booking Details**")
        c = st.columns(5)
        with c[0]:
            booking_number = st.text_input(
                "booking_details.booking_number",
                value=deep_get(payload, "booking_details.booking_number", "")
            )
        with c[1]:
            payment_reference = st.text_input(
                "booking_details.payment_reference",
                value=deep_get(payload, "booking_details.payment_reference", "")
            )
        with c[2]:
            check_in = st.date_input(
                "booking_details.check_in",
                value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today())))
            )
        with c[3]:
            check_out = st.date_input(
                "booking_details.check_out",
                value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today())))
            )

        submitted = st.form_submit_button("Submit")

    if submitted:
        items = payload.get("items", [])  # keep read-only

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
                "location": (seller_location or "").strip() or None
            },
            "buyer": {
                "name": buyer_name,
                "email": buyer_email
            },
            "booking_details": {
                "booking_number": booking_number,
                "payment_reference": payment_reference,
                "check_in": to_iso(check_in),
                "check_out": to_iso(check_out),
            },
            "total": round(float(total), 2),
            "category": category or "hotel"
        }

        st.session_state.last_payload = payload_out
        st.session_state.ui_step = "form"

        # Write to DB
        try:
            claim_id = save_expense_claim(payload_out)
            st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
        except Exception as e:
            st.error(f"❌ Database insert failed: {e}")

    # Read-only extracted items
    if isinstance(payload.get("items", None), list):
        with st.expander("View extracted items (read-only)"):
            st.json(payload["items"])

    # Validate final JSON
    if st.session_state.get("last_payload"):
        st.markdown("---")
        st.write("**⚙️ Validate the Final JSON (after your review)**")
        if st.button("✅ Submit & Validate", key="run_agent_validate", use_container_width=True):
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

# -------------------------------------------------
# DASHBOARD WRAPPER
# -------------------------------------------------
def dashboard(emp_id: str):
    # extractor_node_ui itself renders header + rest
    extractor_node_ui(emp_id, OUTPUT_DIR, input_dir)

# -------------------------------------------------
# INIT LOCAL (PER-PAGE) STATE FOR EXTRACTOR UI
# -------------------------------------------------
for key, default in {
    "ui_step": "idle",               # "idle" | "form"
    "extraction_resp": None,
    "extracted_payload": None,
    "uploaded_image_path": None,
    "last_payload": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------------------------------
# PAGE RENDER
# -------------------------------------------------

# 1. Make sure user is allowed here
ensure_employee_allowed()

# 2. Sidebar info / cross-nav
st.sidebar.write(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=do_logout_and_return)

# If manager, show button to jump
if st.session_state.access_label == "M":
    st.sidebar.button("Manager View", on_click=go_manager)

# If finance-capable user somehow lands here, let them jump
if (
    st.session_state.access_label == "F"
    or (st.session_state.get("email", "").lower() == "finance@company.com")
):
    st.sidebar.button("Finance View", on_click=go_finance)

# 3. Load employee metadata (emp_id etc.) if not present
if not st.session_state.get("emp_id"):
    details = _agent.load_employee_by_email(st.session_state.email)
    if details:
        st.session_state.emp_id = details.get("employee_id")
        st.session_state.grade = details.get("grade")
        st.session_state.manager_id = details.get("manager_id")
        st.session_state.first_name = details.get("first_name")

# 4. Greeting
emp_name_display = st.session_state.get("first_name") or st.session_state.email
st.subheader(f"Welcome, {emp_name_display}! 👋")

# 5. MAIN CONTENT TABS instead of sidebar radio
tab_upload, tab_claims, tab_approve = st.tabs(
    ["📤 Upload Bill", "💼 Claims Dashboard", "📜 Bill Approve"]
)

with tab_upload:
    dashboard(st.session_state.get("emp_id"))

with tab_claims:
    show_claims_dashboard()


def manager_approve():
        # Only managers should see this tab meaningfully
    if st.session_state.get("access_label") != "M":
        st.warning("You do not have manager approval rights.")
    else:
        mgr_id = st.session_state.get("emp_id")

        if not mgr_id:
            st.error("Cannot resolve your manager ID (emp_id missing in session). Please re-login.")
        else:
            try:
                pending_df = db_utils.load_manager_pending_claims(mgr_id, limit=100)

                st.write(pending_df)

                if pending_df is None or pending_df.empty:
                    st.info("🎉 No pending claims from your direct reports.")
                else:
                    st.caption(
                        "These are expense claims from your direct reports currently in 'Pending Review'."
                    )

                    st.dataframe(
                        pending_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "claim_id": "Claim ID",
                            "user_name": "Employee Name",
                            "claim_type": "Claim Type",
                            "amount": st.column_config.NumberColumn(format="₹ %.2f"),
                            "currency": "Currency",
                            "status": "Status",
                            "vendor_name": "Vendor",
                            "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
                        },
                    )

                    with st.expander("Raw data (debug)"):
                        st.write(pending_df)

            except Exception as e:
                st.error(f"Failed to load pending approvals: {e}")


with tab_approve:
    manager_approve()
    

