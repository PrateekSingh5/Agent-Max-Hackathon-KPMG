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
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.access_label = None
    st.session_state.allowed_views = []
    st.switch_page("portal_login.py")

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
            st.switch_page("portal_login.py")
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
# CATEGORY-SPECIFIC FORMS
# -------------------------------------------------

def render_form_hotel(payload, emp_id):
    with st.form(key="invoice_form_hotel", clear_on_submit=False):
        st.write("**Hotel Invoice / Stay Details**")

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
            vendor = st.text_input("hotel / vendor name", value=payload.get("vendor", "") or deep_get(payload, "seller.hotel_name", ""))
        with c[4]:
            currency = st.text_input("currency", value=payload.get("currency", "INR"))

        c = st.columns(5)
        with c[0]:
            invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
        with c[1]:
            inv_date = st.date_input(
                "invoice date",
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
        st.write("**Buyer (Employee)**")
        c = st.columns(2)
        with c[0]:
            buyer_name = st.text_input("buyer.name", value=deep_get(payload, "buyer.name", ""))
        with c[1]:
            buyer_email = st.text_input("buyer.email", value=deep_get(payload, "buyer.email", ""))

        st.write("**Hotel / Seller**")
        c = st.columns(2)
        with c[0]:
            seller_hotel = st.text_input("seller.hotel_name", value=deep_get(payload, "seller.hotel_name", ""))
        with c[1]:
            seller_location = st.text_input("seller.location", value=deep_get(payload, "seller.location", "") or "")

        st.markdown("---")
        st.write("**Booking Details**")
        c = st.columns(4)
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
                "check_in",
                value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today())))
            )
        with c[3]:
            check_out = st.date_input(
                "check_out",
                value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today())))
            )

        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    payload_out = {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(expense_date),
        "vendor": vendor,
        "total_amount": round(float(total_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),  # keep read-only
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
    return payload_out


def render_form_travel(payload, emp_id):
    # Assumed travel schema
    # e.g. {
    #   "from_city": "...",
    #   "to_city": "...",
    #   "travel_mode": "flight/train/cab",
    #   "travel_date": "2025-01-02",
    #   "ticket_amount": 1234.5,
    #   "currency": "INR",
    #   "vendor": "IndiGo",
    #   ...
    # }
    with st.form(key="invoice_form_travel", clear_on_submit=False):
        st.write("**Travel Claim Details**")

        c = st.columns(4)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            travel_mode = st.text_input("Mode (flight/train/cab)", value=payload.get("travel_mode", ""))
        with c[2]:
            from_city = st.text_input("From City", value=payload.get("from_city", ""))
        with c[3]:
            to_city = st.text_input("To City", value=payload.get("to_city", ""))

        c = st.columns(4)
        with c[0]:
            travel_date = st.date_input(
                "Travel Date",
                value=parse_iso_date(payload.get("travel_date", to_iso(date.today())))
            )
        with c[1]:
            vendor = st.text_input("Vendor / Airline / Agency", value=payload.get("vendor", ""))
        with c[2]:
            ticket_amount = st.number_input(
                "Ticket Amount",
                value=float(payload.get("ticket_amount", payload.get("total_amount", 0.0) or 0.0)),
                step=1.0,
                min_value=0.0
            )
        with c[3]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        c = st.columns(2)
        with c[0]:
            expense_date = st.date_input(
                "Expense Booking Date",
                value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
            )
        with c[1]:
            invoice_id = st.text_input("Invoice / Ticket ID", value=payload.get("invoice_id", ""))

        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    payload_out = {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(expense_date),
        "vendor": vendor,
        "total_amount": round(float(ticket_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "travel_details": {
            "from_city": from_city,
            "to_city": to_city,
            "travel_mode": travel_mode,
            "travel_date": to_iso(travel_date),
        },
        "category": "travel",
    }
    return payload_out


def render_form_food(payload, emp_id):
    # Assume food schema:
    # {
    #   "restaurant": "...",
    #   "meal_date": "2025-01-04",
    #   "total_amount": 560.0,
    #   "currency": "INR",
    #   "attendees": ["...","..."],
    #   ...
    # }
    with st.form(key="invoice_form_food", clear_on_submit=False):
        st.write("**Food / Meal Claim Details**")

        c = st.columns(3)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            restaurant = st.text_input("Restaurant / Vendor", value=payload.get("restaurant", payload.get("vendor", "")))
        with c[2]:
            meal_date = st.date_input(
                "Meal Date",
                value=parse_iso_date(payload.get("meal_date", payload.get("expense_date", to_iso(date.today()))))
            )

        c = st.columns(3)
        with c[0]:
            total_amount = st.number_input(
                "Bill Amount",
                value=float(payload.get("total_amount", 0.0) or 0.0),
                step=1.0,
                min_value=0.0
            )
        with c[1]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))
        with c[2]:
            invoice_id = st.text_input("Bill / Invoice ID", value=payload.get("invoice_id", ""))

        attendees = st.text_input(
            "Attendees (comma-separated)",
            value=", ".join(payload.get("attendees", []))
        )

        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    payload_out = {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(meal_date),
        "vendor": restaurant,
        "total_amount": round(float(total_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "food_details": {
            "attendees": [a.strip() for a in attendees.split(",") if a.strip()],
        },
        "category": "food",
    }
    return payload_out


def render_form_local_conv(payload, emp_id):
    # Assume local conveyance schema:
    # {
    #   "city": "Bangalore",
    #   "ride_date": "2025-01-05",
    #   "distance_km": 14.2,
    #   "fare_amount": 320,
    #   "currency": "INR",
    #   "vendor": "Uber",
    # }
    with st.form(key="invoice_form_local", clear_on_submit=False):
        st.write("🚕 Local Conveyance / Taxi / Auto")

        c = st.columns(4)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            city = st.text_input("City", value=payload.get("city", ""))
        with c[2]:
            ride_date = st.date_input(
                "Ride Date",
                value=parse_iso_date(payload.get("ride_date", payload.get("expense_date", to_iso(date.today()))))
            )
        with c[3]:
            vendor = st.text_input("Vendor (Uber/Ola/etc.)", value=payload.get("vendor", ""))

        c = st.columns(3)
        with c[0]:
            distance_km = st.number_input(
                "Distance (km)",
                value=float(payload.get("distance_km", 0.0) or 0.0),
                step=0.5,
                min_value=0.0
            )
        with c[1]:
            fare_amount = st.number_input(
                "Fare Amount",
                value=float(payload.get("fare_amount", payload.get("total_amount", 0.0) or 0.0)),
                step=1.0,
                min_value=0.0
            )
        with c[2]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        invoice_id = st.text_input("Trip / Ride ID", value=payload.get("invoice_id", ""))

        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    payload_out = {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(ride_date),
        "vendor": vendor,
        "total_amount": round(float(fare_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "local_conveyance_details": {
            "city": city,
            "distance_km": float(distance_km),
        },
        "category": "local_conveyance",
    }
    return payload_out


def render_form_other(payload, emp_id):
    # Generic fallback
    with st.form(key="invoice_form_other", clear_on_submit=False):
        st.write("Other / Misc Expense")

        c = st.columns(3)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            vendor = st.text_input("Vendor / Source", value=payload.get("vendor", ""))
        with c[2]:
            expense_date = st.date_input(
                "Expense Date",
                value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
            )

        c = st.columns(3)
        with c[0]:
            description = st.text_input("Description", value=payload.get("description", ""))
        with c[1]:
            amount = st.number_input(
                "Amount",
                value=float(payload.get("total_amount", 0.0) or 0.0),
                step=1.0,
                min_value=0.0
            )
        with c[2]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        invoice_id = st.text_input("Reference / Invoice ID", value=payload.get("invoice_id", ""))

        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    payload_out = {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(expense_date),
        "vendor": vendor,
        "total_amount": round(float(amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "other_details": {
            "description": description,
        },
        "category": payload.get("category", "other") or "other",
    }
    return payload_out


def render_dynamic_form(payload, emp_id):
    """
    Pick which form to render based on payload['category'].
    Returns a normalized payload_out dict if the user clicked Submit,
    else None.
    """
    cat = (payload.get("category") or "").strip().lower()
    if cat == "hotel":
        return render_form_hotel(payload, emp_id)
    elif cat == "travel":
        return render_form_travel(payload, emp_id)
    elif cat == "food":
        return render_form_food(payload, emp_id)
    elif cat in ["local", "local_conveyance", "local conveyance", "local_convey"]:
        return render_form_local_conv(payload, emp_id)
    else:
        # default "other"
        return render_form_other(payload, emp_id)

# -------------------------------------------------
# EXTRACTOR NODE UI
# -------------------------------------------------
def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
    """
    Flow:
    1. Upload file
    2. Click Review -> call /api/Agent?image_name=...&emp_id=...
       body: { phase:"extract", json_out_dir, save_json_file }
    3. We store extraction payload in session.
    4. We render a category-specific form.
    5. On submit of that form:
       - save_expense_claim(payload_out)
       - keep payload_out as last_payload for validation
    6. User can click "Submit & Validate" -> /api/Agent?phase=validate
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

        # save uploaded file locally
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", uploaded_file.name)
        file_path = input_dir / safe_name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            # IMPORTANT: fix 422 by passing required query params separately
            params = {
                "image_name": str(file_path),
                "emp_id": emp_id,
            }
            body = {
                "phase": "extract",
                "json_out_dir": output_dir,
                "save_json_file": True,
            }

            r = requests.post(AGENT_ENDPOINT, params=params, json=body, timeout=120)
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

    # Render payload / raw preview
    payload = st.session_state.extracted_payload or {}
    if not isinstance(payload, dict) or not payload:
        st.warning("No payload returned from API.")
        if st.session_state.extraction_resp:
            with st.expander("Raw API response"):
                st.json(st.session_state.extraction_resp)
        return

    with st.expander("Raw extraction payload"):
        st.json(payload)

    # --- Dynamic category form ---
    payload_out = render_dynamic_form(payload, emp_id)

    if payload_out is not None:
        # user clicked Submit inside the category form
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
        with st.expander("View extracted line items (read-only)"):
            st.json(payload["items"])

    # Validate final JSON (only if we have last_payload)
    if st.session_state.get("last_payload"):
        st.markdown("---")
        st.write("**⚙️ Validate the Final JSON (after your review)**")
        if st.button("✅ Submit & Validate", key="run_agent_validate", use_container_width=True):
            try:
                # For validate phase we assume FastAPI expects phase in query OR body.
                # We'll send as query param 'phase=validate' + full JSON body.
                r = requests.post(
                    AGENT_ENDPOINT,
                    params={"phase": "validate"},
                    json=st.session_state.last_payload,
                    timeout=120
                )
                st.write(f"**Status:** {r.status_code}")
                try:
                    st.json(r.json())
                except ValueError:
                    st.code(r.text)
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {e}")

# -------------------------------------------------
# DASHBOARD WRAPPER
# -------------------------------------------------
def dashboard(emp_id: str):
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

# 5. MAIN CONTENT TABS
tab_upload, tab_claims = st.tabs(["📤 Upload Bill", "💼 Claims Dashboard"])

with tab_upload:
    dashboard(st.session_state.get("emp_id"))

with tab_claims:
    show_claims_dashboard()