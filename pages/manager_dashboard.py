# # manager_dashboard.py
import os
import re
import json
from pathlib import Path
from datetime import date, datetime
import requests
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import agent as _agent  # must expose load_employee_by_email(...)


from db_utils import save_expense_claim, log_validation_result, load_manager_team_pending_claims , load_recent_claims
import db_utils
# from claims_dashboard import load_recent_claims

# Email utils (uses SMTP creds from utils.py)
import utils as mail_utils

# -------------------------------------------------
# PAGE CONFIG (must be first Streamlit call)
# -------------------------------------------------
st.set_page_config(page_title="Manager Dashboard", layout="wide")

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------
BASE_API = "http://localhost:8000"
AGENT_ENDPOINT = f"{BASE_API}/api/Agent"

OUTPUT_DIR = "output/langchain_json"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

input_dir = Path("./input/images")
input_dir.mkdir(parents=True, exist_ok=True)

# >>> HARD-CODED RECIPIENT (per request) <<<
RECIPIENT_OVERRIDE = "kumar.vipin.official@gmail.com"



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
        st.error("Access denied. Employee/Manager portal only.")
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
# CLAIMS DASHBOARD (for this manager's own claims)
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
# CATEGORY-SPECIFIC FORMS (same schema as employee view)
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
            expense_date = st.date_input("expense_date", value=parse_iso_date(payload.get("expense_date", to_iso(date.today()))))
        with c[3]:
            vendor = st.text_input("hotel / vendor name", value=payload.get("vendor", "") or deep_get(payload, "seller.hotel_name", ""))
        with c[4]:
            currency = st.text_input("currency", value=payload.get("currency", "INR"))

        c = st.columns(5)
        with c[0]:
            invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
        with c[1]:
            inv_date = st.date_input("invoice date", value=parse_iso_date(payload.get("date", to_iso(date.today()))))
        with c[2]:
            total_amount = st.number_input("total_amount", value=float(payload.get("total_amount", 0.0) or 0.0), step=1.0, min_value=0.0)
        with c[3]:
            total = st.number_input("total", value=float(payload.get("total", 0.0) or 0.0), step=1.0, min_value=0.0)
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
            booking_number = st.text_input("booking_details.booking_number", value=deep_get(payload, "booking_details.booking_number", ""))
        with c[1]:
            payment_reference = st.text_input("booking_details.payment_reference", value=deep_get(payload, "booking_details.payment_reference", ""))
        with c[2]:
            check_in = st.date_input("check_in", value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today()))))
        with c[3]:
            check_out = st.date_input("check_out", value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today()))))
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    return {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(expense_date),
        "vendor": vendor,
        "total_amount": round(float(total_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "invoice_number": invoice_number,
        "date": to_iso(inv_date),
        "seller": {"hotel_name": seller_hotel, "location": (seller_location or "").strip() or None},
        "buyer": {"name": buyer_name, "email": buyer_email},
        "booking_details": {
            "booking_number": booking_number,
            "payment_reference": payment_reference,
            "check_in": to_iso(check_in),
            "check_out": to_iso(check_out),
        },
        "total": round(float(total), 2),
        "category": category or "hotel",
    }

def render_form_travel(payload, emp_id):
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
            travel_date = st.date_input("Travel Date", value=parse_iso_date(payload.get("travel_date", to_iso(date.today()))))
        with c[1]:
            vendor = st.text_input("Vendor / Airline / Agency", value=payload.get("vendor", ""))
        with c[2]:
            ticket_amount = st.number_input("Ticket Amount", value=float(payload.get("ticket_amount", payload.get("total_amount", 0.0) or 0.0)), step=1.0, min_value=0.0)
        with c[3]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        c = st.columns(2)
        with c[0]:
            expense_date = st.date_input("Expense Booking Date", value=parse_iso_date(payload.get("expense_date", to_iso(date.today()))))
        with c[1]:
            invoice_id = st.text_input("Invoice / Ticket ID", value=payload.get("invoice_id", ""))
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    return {
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

def render_form_food(payload, emp_id):
    with st.form(key="invoice_form_food", clear_on_submit=False):
        st.write("**Food / Meal Claim Details**")
        c = st.columns(3)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            restaurant = st.text_input("Restaurant / Vendor", value=payload.get("restaurant", payload.get("vendor", "")))
        with c[2]:
            meal_date = st.date_input("Meal Date", value=parse_iso_date(payload.get("meal_date", payload.get("expense_date", to_iso(date.today())))))
        c = st.columns(3)
        with c[0]:
            total_amount = st.number_input("Bill Amount", value=float(payload.get("total_amount", 0.0) or 0.0), step=1.0, min_value=0.0)
        with c[1]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))
        with c[2]:
            invoice_id = st.text_input("Bill / Invoice ID", value=payload.get("invoice_id", ""))
        attendees = st.text_input("Attendees (comma-separated)", value=", ".join(payload.get("attendees", [])))
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    return {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(meal_date),
        "vendor": restaurant,
        "total_amount": round(float(total_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "food_details": {"attendees": [a.strip() for a in attendees.split(",") if a.strip()]},
        "category": "food",
    }

def render_form_local_conv(payload, emp_id):
    with st.form(key="invoice_form_local", clear_on_submit=False):
        st.write("🚕 Local Conveyance / Taxi / Auto")
        c = st.columns(4)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            city = st.text_input("City", value=payload.get("city", ""))
        with c[2]:
            ride_date = st.date_input("Ride Date", value=parse_iso_date(payload.get("ride_date", payload.get("expense_date", to_iso(date.today())))))
        with c[3]:
            vendor = st.text_input("Vendor (Uber/Ola/etc.)", value=payload.get("vendor", ""))

        c = st.columns(3)
        with c[0]:
            distance_km = st.number_input("Distance (km)", value=float(payload.get("distance_km", 0.0) or 0.0), step=0.5, min_value=0.0)
        with c[1]:
            fare_amount = st.number_input("Fare Amount", value=float(payload.get("fare_amount", payload.get("total_amount", 0.0) or 0.0)), step=1.0, min_value=0.0)
        with c[2]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        invoice_id = st.text_input("Trip / Ride ID", value=payload.get("invoice_id", ""))
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    return {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(ride_date),
        "vendor": vendor,
        "total_amount": round(float(fare_amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "local_conveyance_details": {"city": city, "distance_km": float(distance_km)},
        "category": "local_conveyance",
    }

def render_form_other(payload, emp_id):
    with st.form(key="invoice_form_other", clear_on_submit=False):
        st.write("Other / Misc Expense")
        c = st.columns(3)
        with c[0]:
            employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
        with c[1]:
            vendor = st.text_input("Vendor / Source", value=payload.get("vendor", ""))
        with c[2]:
            expense_date = st.date_input("Expense Date", value=parse_iso_date(payload.get("expense_date", to_iso(date.today()))))

        c = st.columns(3)
        with c[0]:
            description = st.text_input("Description", value=payload.get("description", ""))
        with c[1]:
            amount = st.number_input("Amount", value=float(payload.get("total_amount", 0.0) or 0.0), step=1.0, min_value=0.0)
        with c[2]:
            currency = st.text_input("Currency", value=payload.get("currency", "INR"))

        invoice_id = st.text_input("Reference / Invoice ID", value=payload.get("invoice_id", ""))
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return None

    return {
        "invoice_id": invoice_id,
        "employee_id": employee_id or emp_id,
        "expense_date": to_iso(expense_date),
        "vendor": vendor,
        "total_amount": round(float(amount), 2),
        "currency": currency,
        "items": payload.get("items", []),
        "other_details": {"description": description},
        "category": payload.get("category", "other") or "other",
    }

# -------------------------------------------------
# EXTRACTOR NODE UI (manager can also submit)
# -------------------------------------------------
def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
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

    if reset_clicked:
        st.session_state.ui_step = "idle"
        st.session_state.extraction_resp = None
        st.session_state.extracted_payload = None
        st.session_state.uploaded_image_path = None
        st.session_state.last_payload = None
        st.success("Extractor state cleared.")
        return

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
            params = {"image_name": str(file_path), "emp_id": emp_id}
            body = {"phase": "extract", "json_out_dir": output_dir, "save_json_file": True}

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

    if st.session_state.ui_step != "form":
        st.info("Upload a file and click **Click to Review** to continue.")
        return

    payload = st.session_state.extracted_payload or {}
    if not isinstance(payload, dict) or not payload:
        st.warning("No payload returned from API.")
        if st.session_state.extraction_resp:
            with st.expander("Raw API response"):
                st.json(st.session_state.extraction_resp)
        return

    with st.expander("Raw extraction payload"):
        st.json(payload)

    payload_out = render_dynamic_form(payload, emp_id)

    if payload_out is not None:
        st.session_state.ui_step = "form"

        # Validate via API
        try:
            r = requests.post(
                AGENT_ENDPOINT,
                params={"phase": "validate"},
                json=payload_out,
                timeout=120
            )
            r.raise_for_status()
            validation_json = r.json() or {}
            # st.write("Validation Payload")
            # st.json(validation_json)
        except requests.exceptions.RequestException as e:
            validation_json = {
                "status": "ValidationError",
                "auto_approved": False,
                "payment_mode": payload_out.get("payment_mode"),
                "error_msg": str(e),
            }

        # st.write("Payload")
        # st.json(payload_out)

        # Persist to DB
        try:
            tag_status = validation_json.get("tag", "Pending")
            # st.write(tag_status)
            claim_id = save_expense_claim(payload_out, tag_status)
            st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
        except Exception as e:
            st.error(f"❌ Database insert failed: {e}")
            st.stop()

        # Log validation
        try:
            summary = log_validation_result(
                claim_id=claim_id,
                employee_id=payload_out.get("employee_id") or emp_id,
                validation_obj=tag_status,
            )
        except Exception as log_ex:
            summary = {"claim_id": claim_id, "status_val": "LogError", "auto_approved": False, "log_error": str(log_ex)}

        # st.info("Validation summary")
        # st.json(summary)

        # with st.expander("Full validation response"):
        #     st.json(validation_json)

        # Email ACK to hardcoded recipient (manager's own submission)
        try:
            tag = validation_json.get("tag", "Pending")
            decision = validation_json.get("decision")
            comments = (
                validation_json.get("comments")
                or deep_get(validation_json, "validation.message")
                or "No additional comments"
            )
            employee_name = st.session_state.get("first_name")  # for salutation
            emp_id_for_email = payload_out.get("employee_id") or st.session_state.get("emp_id")
            category = (payload_out.get("category") or "other").title()
            amount = payload_out.get("total_amount", 0.0)
            currency = payload_out.get("currency", "INR")
            vendor = payload_out.get("vendor")
            expense_date = payload_out.get("expense_date")

            subject, body = mail_utils.draft_employee_ack_on_upload(
                claim_id=claim_id,
                employee_name=employee_name,
                employee_id=emp_id_for_email,
                category=category,
                amount=amount,
                currency=currency,
                vendor=vendor,
                expense_date=expense_date,
                tag=tag,
                decision=decision,
                comments=comments,
            )
            sent = mail_utils.send_email(RECIPIENT_OVERRIDE, subject, body)
            if sent:
                st.success(f"📧 Acknowledgement sent to {RECIPIENT_OVERRIDE}")
            else:
                st.warning(f"Could not send email to {RECIPIENT_OVERRIDE}. Check SMTP credentials/connectivity.")
        except Exception as e:
            st.warning(f"Email step failed: {e}")

# -------------------------------------------------
# Manager Approval helpers (DB + email)
# -------------------------------------------------
def _get_engine():
    # Reuse a single engine per run
    if "_manager_engine" not in st.session_state:
        db_url = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL", "")
        if not db_url:
            raise RuntimeError("DATABASE_URL not configured in env or st.secrets")
        st.session_state._manager_engine = create_engine(db_url, future=True)
    return st.session_state._manager_engine

def _update_claim_decision_fallback(claim_id: str, decision: str, comment: str, approver_id: str):
    """
    Fallback direct-SQL updater if db_utils.manager_update_claim_decision is not available.
    Safest path: update only status. (Uncomment richer version if your schema has columns)
    """
    engine = _get_engine()
    sql_basic = text("""
        UPDATE expense_claims
        SET status = :status
        WHERE claim_id = :claim_id
    """)
    # If you have manager_comment / manager_id columns, switch to:
    # sql_with_comment = text("""
    #     UPDATE expense_claims
    #     SET status = :status,
    #         manager_comment = :comment,
    #         manager_id = :mgr_id
    #     WHERE claim_id = :claim_id
    # """)
    with engine.begin() as conn:
        conn.execute(sql_basic, {
            "status": "Approved" if decision == "Approve" else "Rejected",
            "claim_id": claim_id,
            # "comment": comment,
            # "mgr_id": approver_id,
        })

def _fetch_claim_row(claim_id: str) -> dict | None:
    """Fetch a minimal claim row for context (optional)."""
    try:
        engine = _get_engine()
        q = text("""
            SELECT ec.claim_id, ec.employee_id, ec.expense_category AS category,
                   ec.amount, ec.currency, ec.vendor_name, ec.claim_date
            FROM expense_claims ec
            WHERE ec.claim_id = :cid
            LIMIT 1
        """)
        with engine.connect() as conn:
            df = pd.read_sql_query(q, conn, params={"cid": claim_id})
        if not df.empty:
            return df.to_dict(orient="records")[0]
    except Exception:
        pass
    return None

def _apply_manager_decisions(rows_to_apply: list[dict], approver_id: str):
    """
    rows_to_apply: list of dicts containing claim_id, Decision, Manager Comment
    1) Update DB via db_utils.manager_update_claim_decision if present, else fallback SQL
    2) Send email to HARD-CODED recipient informing decision
    """
    # Prefer db_utils.manager_update_claim_decision if present
    import db_utils as _dbu
    updater = getattr(_dbu, "manager_update_claim_decision", None)

    successes, failures = [], []
    for r in rows_to_apply:
        claim_id = str(r.get("claim_id", "")).strip()
        decision = str(r.get("Decision", "")).strip()       # "Approve" | "Reject"
        comment  = str(r.get("Manager Comment", "")).strip()
        if not claim_id or decision not in {"Approve", "Reject"}:
            continue
        try:
            if callable(updater):
                updater(claim_id, decision, comment, approver_id)
            else:
                _update_claim_decision_fallback(claim_id, decision, comment, approver_id)
            successes.append(claim_id)

            # --- Email notify to HARD-CODED recipient ---
            claim = _fetch_claim_row(claim_id)
            employee_name = None
            emp_id_for_email = None
            if claim:
                emp_id_for_email = claim.get("employee_id")
            sub, body = mail_utils.draft_employee_update_on_action(
                claim_id=claim_id,
                employee_name=employee_name,  # unknown here; optional
                employee_id=emp_id_for_email or "—",
                actor_role="Manager",
                decision="Approved" if decision == "Approve" else "Rejected",
                comment=comment,
            )
            mail_utils.send_email(RECIPIENT_OVERRIDE, sub, body)

        except Exception as ex:
            failures.append((claim_id, str(ex)))
    return successes, failures


# -------------------------------------------------
# Manager Approval UI
# -------------------------------------------------
def manager_approve():
    """
    Manager view:
      - shows pending team claims
      - adds editable 'Decision' (Approve/Reject) and 'Manager Comment'
      - writes decision to DB and refreshes table
      - sends HARD-CODED email notifications
    """
    if st.session_state.get("access_label") != "M":
        st.warning("You do not have manager approval rights.")
        return

    mgr_email = st.session_state.get("email", None)
    mgr_emp_id = st.session_state.get("emp_id", None)

    try:
        df = load_manager_team_pending_claims(
            manager_email=mgr_email,
            manager_id=mgr_emp_id,
        )
        if df is None or df.empty:
            st.info("No pending claims from your direct reports.")
            return

        work = df.copy()
        if "Decision" not in work.columns:
            work["Decision"] = ""
        if "Manager Comment" not in work.columns:
            work["Manager Comment"] = ""

        st.markdown("### Pending Claims (Manager Review)")
        edited = st.data_editor(
            work,
            use_container_width=True,
            hide_index=True,
            column_config={
                "claim_id": "Claim ID",
                "employee_id": "Employee ID",
                "user_name": "Employee Name",
                "claim_type": "Claim Type",
                "amount": st.column_config.NumberColumn(format="₹ %.2f"),
                "currency": "Currency",
                "status": "Status",
                "vendor_name": "Vendor",
                "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
                "Decision": st.column_config.SelectboxColumn(
                    "Decision",
                    options=["", "Approve", "Reject"],
                    required=False,
                    help="Choose Approve or Reject for each claim you want to act on."
                ),
                "Manager Comment": st.column_config.TextColumn(
                    "Manager Comment",
                    help="Optional note that will be stored with the decision."
                ),
            },
            disabled=[
                "claim_id", "employee_id", "user_name", "claim_type",
                "amount", "currency", "status", "vendor_name", "claim_date"
            ],
            key="manager_editor",
        )

        c1, c2 = st.columns([1, 3])
        with c1:
            do_submit = st.button("Submit decisions", use_container_width=True)
        with c2:
            st.caption("Tip: leave Decision blank to skip a row.")

        if do_submit:
            rows = edited.fillna("").to_dict(orient="records")
            to_apply = [r for r in rows if r.get("Decision") in {"Approve", "Reject"}]

            if not to_apply:
                st.info("No decisions to apply.")
                return

            ok, bad = _apply_manager_decisions(to_apply, approver_id=mgr_emp_id)

            if ok:
                st.success(f"Updated {len(ok)} claim(s): {', '.join(ok)}")
            if bad:
                st.error("Some updates failed:")
                for cid, msg in bad:
                    st.write(f"- {cid}: {msg}")

            if ok:
                remaining = edited[~edited["claim_id"].isin(ok)].drop(columns=["Decision", "Manager Comment"], errors="ignore")
                if remaining.empty:
                    st.info("All pending items are processed. 🎉")
                else:
                    st.markdown("#### Remaining Pending Items")
                    st.dataframe(
                        remaining,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "claim_id": "Claim ID",
                            "employee_id": "Employee ID",
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
        st.error(f"Failed to load pending approvals: {e}")

# -------------------------------------------------
# PAGE RENDER
# -------------------------------------------------
ensure_employee_allowed()

st.sidebar.write(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=do_logout_and_return)

# Manager View button (you're already here, but keep for consistency)
if st.session_state.access_label == "M":
    st.sidebar.button("Manager View", on_click=go_manager, disabled=True)

# If finance-capable user, allow quick jump
if (st.session_state.get("email", "").lower() == "finance@company.com") or st.session_state.access_label == "F":
    st.sidebar.button("Finance View", on_click=go_finance)

# Bootstrap session employee info
if not st.session_state.get("emp_id"):
    details = db_utils.load_employee_by_email(st.session_state.email)
    if details:
        st.session_state.emp_id = details.get("employee_id")
        st.session_state.grade = details.get("grade")
        st.session_state.manager_id = details.get("manager_id")
        st.session_state.first_name = details.get("first_name")

emp_name_display = st.session_state.get("first_name") or st.session_state.email
st.subheader(f"Welcome, {emp_name_display}! 👋")

# Init per-page state for extractor UI
for key, default in {
    "ui_step": "idle",
    "extraction_resp": None,
    "extracted_payload": None,
    "uploaded_image_path": None,
    "last_payload": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Tabs: Upload (optional), Claims Dashboard, Manager Approvals
tab_upload, tab_claims, tab_approve = st.tabs(["📤 Upload Bill", "💼 Claims Dashboard", "📜 Bill Approve"])

with tab_upload:
    # ✅ FIXED: pass all required args
    extractor_node_ui(st.session_state.get("emp_id"), OUTPUT_DIR, input_dir)

with tab_claims:
    show_claims_dashboard()

with tab_approve:
    manager_approve()
