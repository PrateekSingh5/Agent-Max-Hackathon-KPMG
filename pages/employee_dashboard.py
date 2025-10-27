
# # employee_dashboard.py
# import os
# import re
# import json
# import time
# from pathlib import Path
# from datetime import date, datetime
# import requests
# import pandas as pd
# import streamlit as st

# import agent as _agent
# import db_utils
# from db_utils import save_expense_claim, log_validation_result, load_recent_claims
# import utils as mail_utils

# st.set_page_config(page_title="Employee Dashboard", layout="wide")

# BASE_API = "http://localhost:8000"
# AGENT_ENDPOINT = f"{BASE_API}/api/Agent"
# OUTPUT_DIR = "output/langchain_json"
# Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# input_dir = Path("./input/images")
# input_dir.mkdir(parents=True, exist_ok=True)

# RECIPIENT_OVERRIDE = "kumar.vipin.official@gmail.com"

# # -------- session/nav helpers (unchanged) --------
# def do_logout_and_return():
#     st.session_state.logged_in = False
#     st.session_state.email = None
#     st.session_state.access_label = None
#     st.session_state.allowed_views = []
#     st.switch_page("portal_login.py")

# def go_manager():
#     st.switch_page("pages/manager_dashboard.py")

# def go_finance():
#     st.switch_page("pages/finance_dashboard.py")

# def ensure_employee_allowed():
#     if not st.session_state.get("logged_in", False):
#         st.error("Please login first.")
#         if st.button("Go to Login"):
#             st.switch_page("portal_login.py")
#         st.stop()
#     access_label = st.session_state.get("access_label", "")
#     if access_label not in {"E", "M"}:
#         st.error("Access denied. Employee portal only.")
#         st.sidebar.button("Logout", on_click=do_logout_and_return)
#         st.stop()

# # -------- misc helpers (unchanged) --------
# def parse_iso_date(s: str) -> date:
#     try:
#         return datetime.strptime(s, "%Y-%m-%d").date()
#     except Exception:
#         return date.today()

# def to_iso(d: date | str | None) -> str | None:
#     if d is None:
#         return None
#     if isinstance(d, str):
#         return d
#     return d.isoformat()

# def deep_get(d, path, default=None):
#     cur = d or {}
#     for part in path.split('.'):
#         if not isinstance(cur, dict) or part not in cur:
#             return default
#         cur = cur[part]
#     return cur

# # -------- claims table --------
# def show_claims_dashboard():
#     st.caption("Showing your most recent claims")
#     employee_id = st.session_state.get("emp_id")
#     if not employee_id:
#         st.warning("⚠️ Missing employee_id in session.")
#         return
#     try:
#         df = load_recent_claims(employee_id, 50)
#         if df is None or df.empty:
#             st.info("You have not submitted any claims yet.")
#         else:
#             st.dataframe(
#                 df,
#                 use_container_width=True,
#                 hide_index=True,
#                 column_config={
#                     "claim_id": "Claim ID",
#                     "user_name": "Employee Name",
#                     "claim_type": "Claim Type",
#                     "amount": st.column_config.NumberColumn(format="₹ %.2f"),
#                     "currency": "Currency",
#                     "status": "Status",
#                     "vendor_name": "Vendor",
#                     "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
#                 },
#             )
#     except Exception as e:
#         st.error(f"Failed to load claims: {e}")

# # -------- dynamic forms (unchanged content) --------
# # (keep your render_form_* functions exactly as in your current file)

# # ----------------------------


# # employee_dashboard.py
# import os
# import re
# import json
# import time
# from pathlib import Path
# from datetime import date, datetime
# import requests
# import pandas as pd
# import streamlit as st

# import agent as _agent
# import db_utils
# from db_utils import save_expense_claim, log_validation_result, load_recent_claims
# import utils as mail_utils

# st.set_page_config(page_title="Employee Dashboard", layout="wide")

# BASE_API = "http://localhost:8000"
# AGENT_ENDPOINT = f"{BASE_API}/api/Agent"
# OUTPUT_DIR = "output/langchain_json"
# Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# input_dir = Path("./input/images")
# input_dir.mkdir(parents=True, exist_ok=True)

# RECIPIENT_OVERRIDE = "kumar.vipin.official@gmail.com"

# # -------- session/nav helpers (unchanged) --------
# def do_logout_and_return():
#     st.session_state.logged_in = False
#     st.session_state.email = None
#     st.session_state.access_label = None
#     st.session_state.allowed_views = []
#     st.switch_page("portal_login.py")

# def go_manager():
#     st.switch_page("pages/manager_dashboard.py")

# def go_finance():
#     st.switch_page("pages/finance_dashboard.py")

# def ensure_employee_allowed():
#     if not st.session_state.get("logged_in", False):
#         st.error("Please login first.")
#         if st.button("Go to Login"):
#             st.switch_page("portal_login.py")
#         st.stop()
#     access_label = st.session_state.get("access_label", "")
#     if access_label not in {"E", "M"}:
#         st.error("Access denied. Employee portal only.")
#         st.sidebar.button("Logout", on_click=do_logout_and_return)
#         st.stop()

# # -------- misc helpers (unchanged) --------
# def parse_iso_date(s: str) -> date:
#     try:
#         return datetime.strptime(s, "%Y-%m-%d").date()
#     except Exception:
#         return date.today()

# def to_iso(d: date | str | None) -> str | None:
#     if d is None:
#         return None
#     if isinstance(d, str):
#         return d
#     return d.isoformat()

# def deep_get(d, path, default=None):
#     cur = d or {}
#     for part in path.split('.'):
#         if not isinstance(cur, dict) or part not in cur:
#             return default
#         cur = cur[part]
#     return cur

# # -------- claims table --------
# def show_claims_dashboard():
#     st.caption("Showing your most recent claims")
#     employee_id = st.session_state.get("emp_id")
#     if not employee_id:
#         st.warning("⚠️ Missing employee_id in session.")
#         return
#     try:
#         df = load_recent_claims(employee_id, 50)
#         if df is None or df.empty:
#             st.info("You have not submitted any claims yet.")
#         else:
#             st.dataframe(
#                 df,
#                 use_container_width=True,
#                 hide_index=True,
#                 column_config={
#                     "claim_id": "Claim ID",
#                     "user_name": "Employee Name",
#                     "claim_type": "Claim Type",
#                     "amount": st.column_config.NumberColumn(format="₹ %.2f"),
#                     "currency": "Currency",
#                     "status": "Status",
#                     "vendor_name": "Vendor",
#                     "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD"),
#                 },
#             )
#     except Exception as e:
#         st.error(f"Failed to load claims: {e}")

# # -------- dynamic forms (unchanged content) --------
# # (keep your render_form_* functions exactly as in your current file)



# def render_dynamic_form(payload, emp_id):
#     """
#     Pick which form to render based on payload['category'].
#     Returns a normalized payload_out dict if the user clicked Submit,
#     else None.
#     """
#     cat = (payload.get("category") or "").strip().lower()
#     if cat == "hotel":
#         return render_form_hotel(payload, emp_id)
#     elif cat == "travel":
#         return render_form_travel(payload, emp_id)
#     elif cat == "food":
#         return render_form_food(payload, emp_id)
#     elif cat in ["local", "local_conveyance", "local conveyance", "local_convey"]:
#         return render_form_local_conv(payload, emp_id)
#     else:
#         # default "other"
#         return render_form_other(payload, emp_id)



# # ----------------


# # -------------------------------------------------
# # CATEGORY-SPECIFIC FORMS
# # -------------------------------------------------
# def render_form_hotel(payload, emp_id):
#     with st.form(key="invoice_form_hotel", clear_on_submit=False):
#         st.write("**Hotel Invoice / Stay Details**")

#         c = st.columns(5)
#         with c[0]:
#             invoice_id = st.text_input("invoice_id", value=payload.get("invoice_id", ""))
#         with c[1]:
#             employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
#         with c[2]:
#             expense_date = st.date_input(
#                 "expense_date",
#                 value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
#             )
#         with c[3]:
#             vendor = st.text_input("hotel / vendor name", value=payload.get("vendor", "") or deep_get(payload, "seller.hotel_name", ""))
#         with c[4]:
#             currency = st.text_input("currency", value=payload.get("currency", "INR"))

#         c = st.columns(5)
#         with c[0]:
#             invoice_number = st.text_input("invoice_number", value=payload.get("invoice_number", ""))
#         with c[1]:
#             inv_date = st.date_input(
#                 "invoice date",
#                 value=parse_iso_date(payload.get("date", to_iso(date.today())))
#             )
#         with c[2]:
#             total_amount = st.number_input(
#                 "total_amount",
#                 value=float(payload.get("total_amount", 0.0) or 0.0),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[3]:
#             total = st.number_input(
#                 "total",
#                 value=float(payload.get("total", 0.0) or 0.0),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[4]:
#             category = st.text_input("category", value=payload.get("category", "hotel"))

#         st.markdown("---")
#         st.write("**Buyer (Employee)**")
#         c = st.columns(2)
#         with c[0]:
#             buyer_name = st.text_input("buyer.name", value=deep_get(payload, "buyer.name", ""))
#         with c[1]:
#             buyer_email = st.text_input("buyer.email", value=deep_get(payload, "buyer.email", ""))

#         st.write("**Hotel / Seller**")
#         c = st.columns(2)
#         with c[0]:
#             seller_hotel = st.text_input("seller.hotel_name", value=deep_get(payload, "seller.hotel_name", ""))
#         with c[1]:
#             seller_location = st.text_input("seller.location", value=deep_get(payload, "seller.location", "") or "")

#         st.markdown("---")
#         st.write("**Booking Details**")
#         c = st.columns(4)
#         with c[0]:
#             booking_number = st.text_input(
#                 "booking_details.booking_number",
#                 value=deep_get(payload, "booking_details.booking_number", "")
#             )
#         with c[1]:
#             payment_reference = st.text_input(
#                 "booking_details.payment_reference",
#                 value=deep_get(payload, "booking_details.payment_reference", "")
#             )
#         with c[2]:
#             check_in = st.date_input(
#                 "check_in",
#                 value=parse_iso_date(deep_get(payload, "booking_details.check_in", to_iso(date.today())))
#             )
#         with c[3]:
#             check_out = st.date_input(
#                 "check_out",
#                 value=parse_iso_date(deep_get(payload, "booking_details.check_out", to_iso(date.today())))
#             )

#         submitted = st.form_submit_button("Submit")

#     if not submitted:
#         return None

#     payload_out = {
#         "invoice_id": invoice_id,
#         "employee_id": employee_id or emp_id,
#         "expense_date": to_iso(expense_date),
#         "vendor": vendor,
#         "total_amount": round(float(total_amount), 2),
#         "currency": currency,
#         "items": payload.get("items", []),  # keep read-only
#         "invoice_number": invoice_number,
#         "date": to_iso(inv_date),
#         "seller": {
#             "hotel_name": seller_hotel,
#             "location": (seller_location or "").strip() or None
#         },
#         "buyer": {
#             "name": buyer_name,
#             "email": buyer_email
#         },
#         "booking_details": {
#             "booking_number": booking_number,
#             "payment_reference": payment_reference,
#             "check_in": to_iso(check_in),
#             "check_out": to_iso(check_out),
#         },
#         "total": round(float(total), 2),
#         "category": category or "hotel"
#     }
#     return payload_out


# def render_form_travel(payload, emp_id):
#     with st.form(key="invoice_form_travel", clear_on_submit=False):
#         st.write("**Travel Claim Details**")

#         c = st.columns(4)
#         with c[0]:
#             employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
#         with c[1]:
#             travel_mode = st.text_input("Mode (flight/train/cab)", value=payload.get("travel_mode", ""))
#         with c[2]:
#             from_city = st.text_input("From City", value=payload.get("from_city", ""))
#         with c[3]:
#             to_city = st.text_input("To City", value=payload.get("to_city", ""))

#         c = st.columns(4)
#         with c[0]:
#             travel_date = st.date_input(
#                 "Travel Date",
#                 value=parse_iso_date(payload.get("travel_date", to_iso(date.today())))
#             )
#         with c[1]:
#             vendor = st.text_input("Vendor / Airline / Agency", value=payload.get("vendor", ""))
#         with c[2]:
#             ticket_amount = st.number_input(
#                 "Ticket Amount",
#                 value=float(payload.get("ticket_amount", payload.get("total_amount", 0.0) or 0.0)),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[3]:
#             currency = st.text_input("Currency", value=payload.get("currency", "INR"))

#         c = st.columns(2)
#         with c[0]:
#             expense_date = st.date_input(
#                 "Expense Booking Date",
#                 value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
#             )
#         with c[1]:
#             invoice_id = st.text_input("Invoice / Ticket ID", value=payload.get("invoice_id", ""))

#         submitted = st.form_submit_button("Submit")

#     if not submitted:
#         return None

#     payload_out = {
#         "invoice_id": invoice_id,
#         "employee_id": employee_id or emp_id,
#         "expense_date": to_iso(expense_date),
#         "vendor": vendor,
#         "total_amount": round(float(ticket_amount), 2),
#         "currency": currency,
#         "items": payload.get("items", []),
#         "travel_details": {
#             "from_city": from_city,
#             "to_city": to_city,
#             "travel_mode": travel_mode,
#             "travel_date": to_iso(travel_date),
#         },
#         "category": "travel",
#     }
#     return payload_out


# def render_form_food(payload, emp_id):
#     with st.form(key="invoice_form_food", clear_on_submit=False):
#         st.write("**Food / Meal Claim Details**")

#         c = st.columns(3)
#         with c[0]:
#             employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
#         with c[1]:
#             restaurant = st.text_input("Restaurant / Vendor", value=payload.get("restaurant", payload.get("vendor", "")))
#         with c[2]:
#             meal_date = st.date_input(
#                 "Meal Date",
#                 value=parse_iso_date(payload.get("meal_date", payload.get("expense_date", to_iso(date.today()))))
#             )

#         c = st.columns(3)
#         with c[0]:
#             total_amount = st.number_input(
#                 "Bill Amount",
#                 value=float(payload.get("total_amount", 0.0) or 0.0),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[1]:
#             currency = st.text_input("Currency", value=payload.get("currency", "INR"))
#         with c[2]:
#             invoice_id = st.text_input("Bill / Invoice ID", value=payload.get("invoice_id", ""))

#         attendees = st.text_input(
#             "Attendees (comma-separated)",
#             value=", ".join(payload.get("attendees", []))
#         )

#         submitted = st.form_submit_button("Submit")

#     if not submitted:
#         return None

#     payload_out = {
#         "invoice_id": invoice_id,
#         "employee_id": employee_id or emp_id,
#         "expense_date": to_iso(meal_date),
#         "vendor": restaurant,
#         "total_amount": round(float(total_amount), 2),
#         "currency": currency,
#         "items": payload.get("items", []),
#         "food_details": {
#             "attendees": [a.strip() for a in attendees.split(",") if a.strip()],
#         },
#         "category": "food",
#     }
#     return payload_out


# def render_form_local_conv(payload, emp_id):
#     with st.form(key="invoice_form_local", clear_on_submit=False):
#         st.write("🚕 Local Conveyance / Taxi / Auto")

#         c = st.columns(4)
#         with c[0]:
#             employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
#         with c[1]:
#             city = st.text_input("City", value=payload.get("city", ""))
#         with c[2]:
#             ride_date = st.date_input(
#                 "Ride Date",
#                 value=parse_iso_date(payload.get("ride_date", payload.get("expense_date", to_iso(date.today()))))
#             )
#         with c[3]:
#             vendor = st.text_input("Vendor (Uber/Ola/etc.)", value=payload.get("vendor", ""))

#         c = st.columns(3)
#         with c[0]:
#             distance_km = st.number_input(
#                 "Distance (km)",
#                 value=float(payload.get("distance_km", 0.0) or 0.0),
#                 step=0.5,
#                 min_value=0.0
#             )
#         with c[1]:
#             fare_amount = st.number_input(
#                 "Fare Amount",
#                 value=float(payload.get("fare_amount", payload.get("total_amount", 0.0) or 0.0)),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[2]:
#             currency = st.text_input("Currency", value=payload.get("currency", "INR"))

#         invoice_id = st.text_input("Trip / Ride ID", value=payload.get("invoice_id", ""))

#         submitted = st.form_submit_button("Submit")

#     if not submitted:
#         return None

#     payload_out = {
#         "invoice_id": invoice_id,
#         "employee_id": employee_id or emp_id,
#         "expense_date": to_iso(ride_date),
#         "vendor": vendor,
#         "total_amount": round(float(fare_amount), 2),
#         "currency": currency,
#         "items": payload.get("items", []),
#         "local_conveyance_details": {
#             "city": city,
#             "distance_km": float(distance_km),
#         },
#         "category": "local_conveyance",
#     }
#     return payload_out


# def render_form_other(payload, emp_id):
#     with st.form(key="invoice_form_other", clear_on_submit=False):
#         st.write("Other / Misc Expense")

#         c = st.columns(3)
#         with c[0]:
#             employee_id = st.text_input("employee_id", value=payload.get("employee_id", emp_id or ""))
#         with c[1]:
#             vendor = st.text_input("Vendor / Source", value=payload.get("vendor", ""))
#         with c[2]:
#             expense_date = st.date_input(
#                 "Expense Date",
#                 value=parse_iso_date(payload.get("expense_date", to_iso(date.today())))
#             )

#         c = st.columns(3)
#         with c[0]:
#             description = st.text_input("Description", value=payload.get("description", ""))
#         with c[1]:
#             amount = st.number_input(
#                 "Amount",
#                 value=float(payload.get("total_amount", 0.0) or 0.0),
#                 step=1.0,
#                 min_value=0.0
#             )
#         with c[2]:
#             currency = st.text_input("Currency", value=payload.get("currency", "INR"))

#         invoice_id = st.text_input("Reference / Invoice ID", value=payload.get("invoice_id", ""))

#         submitted = st.form_submit_button("Submit")

#     if not submitted:
#         return None

#     payload_out = {
#         "invoice_id": invoice_id,
#         "employee_id": employee_id or emp_id,
#         "expense_date": to_iso(expense_date),
#         "vendor": vendor,
#         "total_amount": round(float(amount), 2),
#         "currency": currency,
#         "items": payload.get("items", []),
#         "other_details": {
#             "description": description,
#         },
#         "category": payload.get("category", "other") or "other",
#     }
#     return payload_out


# def render_dynamic_form(payload, emp_id):
#     """
#     Pick which form to render based on payload['category'].
#     Returns a normalized payload_out dict if the user clicked Submit,
#     else None.
#     """
#     cat = (payload.get("category") or "").strip().lower()
#     if cat == "hotel":
#         return render_form_hotel(payload, emp_id)
#     elif cat == "travel":
#         return render_form_travel(payload, emp_id)
#     elif cat == "food":
#         return render_form_food(payload, emp_id)
#     elif cat in ["local", "local_conveyance", "local conveyance", "local_convey"]:
#         return render_form_local_conv(payload, emp_id)
#     else:
#         # default "other"
#         return render_form_other(payload, emp_id)




# # -------- extractor UI (only change is log_validation_result input) --------
# def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
#     uploaded_file = st.file_uploader(
#         "Upload invoice/receipt (PNG/JPG/JPEG/WEBP/PDF)",
#         type=["png", "jpg", "jpeg", "webp", "pdf"],
#         accept_multiple_files=False,
#         key="uploader_invoice_image",
#     )

#     c1, c2 = st.columns([1, 1])
#     with c1:
#         run_clicked = st.button("Click to Review", use_container_width=True, key="run_extractor_btn")
#     with c2:
#         reset_clicked = st.button("Reset", use_container_width=True, key="reset_extractor_btn")

#     if reset_clicked:
#         st.session_state.ui_step = "idle"
#         st.session_state.extraction_resp = None
#         st.session_state.extracted_payload = None
#         st.session_state.uploaded_image_path = None
#         st.session_state.last_payload = None
#         st.success("Extractor state cleared.")
#         return

#     if run_clicked:
#         if not emp_id:
#             st.warning("Please log in again: no emp_id in session.")
#             return
#         if not uploaded_file:
#             st.warning("Please upload an image/PDF file first.")
#             return

#         safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", uploaded_file.name)
#         file_path = input_dir / safe_name
#         with open(file_path, "wb") as f:
#             f.write(uploaded_file.getbuffer())

#         try:
#             params = {"image_name": str(file_path), "emp_id": emp_id}
#             body = {"phase": "extract", "json_out_dir": output_dir, "save_json_file": True}
#             r = requests.post(AGENT_ENDPOINT, params=params, json=body, timeout=120)
#             if r.status_code != 200:
#                 st.error(f"API error {r.status_code}: {r.text}")
#                 return
#             resp = r.json() or {}
#             payload = deep_get(resp, "extraction.payload", {}) or {}
#             st.session_state.uploaded_image_path = str(file_path)
#             st.session_state.extraction_resp = resp
#             st.session_state.extracted_payload = payload
#             st.session_state.ui_step = "form"
#             st.success("Extraction complete ✅")
#             st.write("**Saved at:**", str(file_path))
#         except requests.exceptions.RequestException as e:
#             st.error(f"Connection error: {e}")
#             return

#     if st.session_state.ui_step != "form":
#         st.info("Upload a file and click **Click to Review** to continue.")
#         return

#     payload = st.session_state.extracted_payload or {}
#     if not isinstance(payload, dict) or not payload:
#         st.warning("No payload returned from API.")
#         if st.session_state.extraction_resp:
#             with st.expander("Raw API response"):
#                 st.json(st.session_state.extraction_resp)
#         return

#     with st.expander("Raw extraction payload"):
#         st.json(payload)

#     payload_out = render_dynamic_form(payload, emp_id)
#     if payload_out is None:
#         return

#     # validate
#     try:
#         r = requests.post(AGENT_ENDPOINT, params={"phase": "validate"}, json=payload_out, timeout=120)
#         r.raise_for_status()
#         validation_json = r.json() or {}
#     except requests.exceptions.RequestException as e:
#         validation_json = {"status": "ValidationError", "auto_approved": False, "error_msg": str(e)}

#     # save claim
#     try:
#         tag_status = validation_json.get('tag', 'Pending')
#         claim_id = save_expense_claim(payload_out, tag_status)
#         st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
#     except Exception as e:
#         st.error(f"❌ Database insert failed: {e}")
#         st.stop()

#     # log validation (PASS THE DICT!)
#     try:
#         _ = log_validation_result(
#             claim_id=claim_id,
#             employee_id=payload_out.get("employee_id") or emp_id,
#             validation_obj=validation_json,  # ← fixed
#         )
#     except Exception as log_ex:
#         st.warning(f"Validation log failed: {log_ex}")

#     # ack email
#     try:
#         tag = validation_json.get("tag", "Pending")
#         decision = validation_json.get("decision")
#         comments = validation_json.get("comments") or deep_get(validation_json, "validation.message") or "No additional comments"
#         employee_name = st.session_state.get("first_name")
#         emp_id_for_email = payload_out.get("employee_id") or st.session_state.get("emp_id")
#         category = (payload_out.get("category") or "other").title()
#         amount = payload_out.get("total_amount", 0.0)
#         currency = payload_out.get("currency", "INR")
#         vendor = payload_out.get("vendor")
#         expense_date = payload_out.get("expense_date")

#         subject, content = mail_utils.draft_employee_ack_on_upload(
#             claim_id=claim_id,
#             employee_name=employee_name,
#             employee_id=emp_id_for_email,
#             category=category,
#             amount=amount,
#             currency=currency,
#             vendor=vendor,
#             expense_date=expense_date,
#             tag=tag,
#             decision=decision,
#             comments=comments,
#         )
#         sent = mail_utils.send_email(RECIPIENT_OVERRIDE, subject, content)
#         if sent:
#             st.success(f"📧 Acknowledgement sent to {RECIPIENT_OVERRIDE}")
#         else:
#             st.warning(f"Could not send email to {RECIPIENT_OVERRIDE}. Check SMTP credentials/connectivity.")
#     except Exception as e:
#         st.warning(f"Email step failed: {e}")

# # -------- page wiring --------
# for key, default in {
#     "ui_step": "idle",
#     "extraction_resp": None,
#     "extracted_payload": None,
#     "uploaded_image_path": None,
#     "last_payload": None,
# }.items():
#     if key not in st.session_state:
#         st.session_state[key] = default

# ensure_employee_allowed()

# st.sidebar.write(f"Logged in as {st.session_state.email}")
# st.sidebar.button("Logout", on_click=do_logout_and_return)
# if st.session_state.access_label == "M":
#     st.sidebar.button("Manager View", on_click=go_manager)
# if st.session_state.access_label == "F" or (st.session_state.get("email", "").lower() == "finance@company.com"):
#     st.sidebar.button("Finance View", on_click=go_finance)

# if not st.session_state.get("emp_id"):
#     details = db_utils.load_employee_by_email(st.session_state.email)
#     if details:
#         st.session_state.emp_id = details.get("employee_id")
#         st.session_state.grade = details.get("grade")
#         st.session_state.manager_id = details.get("manager_id")
#         st.session_state.first_name = details.get("first_name")

# emp_name_display = st.session_state.get("first_name") or st.session_state.email
# st.subheader(f"Welcome, {emp_name_display}! 👋")

# tab_upload, tab_claims = st.tabs(["📤 Upload Bill", "💼 Claims Dashboard"])
# with tab_upload:
#     extractor_node_ui(st.session_state.get("emp_id"), OUTPUT_DIR, input_dir)
# with tab_claims:
#     show_claims_dashboard()




# # -------- extractor UI (only change is log_validation_result input) --------
# def extractor_node_ui(emp_id: str, output_dir: str, input_dir: Path):
#     uploaded_file = st.file_uploader(
#         "Upload invoice/receipt (PNG/JPG/JPEG/WEBP/PDF)",
#         type=["png", "jpg", "jpeg", "webp", "pdf"],
#         accept_multiple_files=False,
#         key="uploader_invoice_image",
#     )

#     c1, c2 = st.columns([1, 1])
#     with c1:
#         run_clicked = st.button("Click to Review", use_container_width=True, key="run_extractor_btn")
#     with c2:
#         reset_clicked = st.button("Reset", use_container_width=True, key="reset_extractor_btn")

#     if reset_clicked:
#         st.session_state.ui_step = "idle"
#         st.session_state.extraction_resp = None
#         st.session_state.extracted_payload = None
#         st.session_state.uploaded_image_path = None
#         st.session_state.last_payload = None
#         st.success("Extractor state cleared.")
#         return

#     if run_clicked:
#         if not emp_id:
#             st.warning("Please log in again: no emp_id in session.")
#             return
#         if not uploaded_file:
#             st.warning("Please upload an image/PDF file first.")
#             return

#         safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", uploaded_file.name)
#         file_path = input_dir / safe_name
#         with open(file_path, "wb") as f:
#             f.write(uploaded_file.getbuffer())

#         try:
#             params = {"image_name": str(file_path), "emp_id": emp_id}
#             body = {"phase": "extract", "json_out_dir": output_dir, "save_json_file": True}
#             r = requests.post(AGENT_ENDPOINT, params=params, json=body, timeout=120)
#             if r.status_code != 200:
#                 st.error(f"API error {r.status_code}: {r.text}")
#                 return
#             resp = r.json() or {}
#             payload = deep_get(resp, "extraction.payload", {}) or {}
#             st.session_state.uploaded_image_path = str(file_path)
#             st.session_state.extraction_resp = resp
#             st.session_state.extracted_payload = payload
#             st.session_state.ui_step = "form"
#             st.success("Extraction complete ✅")
#             st.write("**Saved at:**", str(file_path))
#         except requests.exceptions.RequestException as e:
#             st.error(f"Connection error: {e}")
#             return

#     if st.session_state.ui_step != "form":
#         st.info("Upload a file and click **Click to Review** to continue.")
#         return

#     payload = st.session_state.extracted_payload or {}
#     if not isinstance(payload, dict) or not payload:
#         st.warning("No payload returned from API.")
#         if st.session_state.extraction_resp:
#             with st.expander("Raw API response"):
#                 st.json(st.session_state.extraction_resp)
#         return

#     with st.expander("Raw extraction payload"):
#         st.json(payload)

#     payload_out = render_dynamic_form(payload, emp_id)
#     if payload_out is None:
#         return

#     # validate
#     try:
#         r = requests.post(AGENT_ENDPOINT, params={"phase": "validate"}, json=payload_out, timeout=120)
#         r.raise_for_status()
#         validation_json = r.json() or {}
#     except requests.exceptions.RequestException as e:
#         validation_json = {"status": "ValidationError", "auto_approved": False, "error_msg": str(e)}

#     # save claim
#     try:
#         tag_status = validation_json.get('tag', 'Pending')
#         claim_id = save_expense_claim(payload_out, tag_status)
#         st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
#     except Exception as e:
#         st.error(f"❌ Database insert failed: {e}")
#         st.stop()

#     # log validation (PASS THE DICT!)
#     try:
#         _ = log_validation_result(
#             claim_id=claim_id,
#             employee_id=payload_out.get("employee_id") or emp_id,
#             validation_obj=validation_json,  # ← fixed
#         )
#     except Exception as log_ex:
#         st.warning(f"Validation log failed: {log_ex}")

#     # ack email
#     try:
#         tag = validation_json.get("tag", "Pending")
#         decision = validation_json.get("decision")
#         comments = validation_json.get("comments") or deep_get(validation_json, "validation.message") or "No additional comments"
#         employee_name = st.session_state.get("first_name")
#         emp_id_for_email = payload_out.get("employee_id") or st.session_state.get("emp_id")
#         category = (payload_out.get("category") or "other").title()
#         amount = payload_out.get("total_amount", 0.0)
#         currency = payload_out.get("currency", "INR")
#         vendor = payload_out.get("vendor")
#         expense_date = payload_out.get("expense_date")

#         subject, content = mail_utils.draft_employee_ack_on_upload(
#             claim_id=claim_id,
#             employee_name=employee_name,
#             employee_id=emp_id_for_email,
#             category=category,
#             amount=amount,
#             currency=currency,
#             vendor=vendor,
#             expense_date=expense_date,
#             tag=tag,
#             decision=decision,
#             comments=comments,
#         )
#         sent = mail_utils.send_email(RECIPIENT_OVERRIDE, subject, content)
#         if sent:
#             st.success(f"📧 Acknowledgement sent to {RECIPIENT_OVERRIDE}")
#         else:
#             st.warning(f"Could not send email to {RECIPIENT_OVERRIDE}. Check SMTP credentials/connectivity.")
#     except Exception as e:
#         st.warning(f"Email step failed: {e}")

# # -------- page wiring --------
# for key, default in {
#     "ui_step": "idle",
#     "extraction_resp": None,
#     "extracted_payload": None,
#     "uploaded_image_path": None,
#     "last_payload": None,
# }.items():
#     if key not in st.session_state:
#         st.session_state[key] = default

# ensure_employee_allowed()

# st.sidebar.write(f"Logged in as {st.session_state.email}")
# st.sidebar.button("Logout", on_click=do_logout_and_return)
# if st.session_state.access_label == "M":
#     st.sidebar.button("Manager View", on_click=go_manager)
# if st.session_state.access_label == "F" or (st.session_state.get("email", "").lower() == "finance@company.com"):
#     st.sidebar.button("Finance View", on_click=go_finance)

# if not st.session_state.get("emp_id"):
#     details = db_utils.load_employee_by_email(st.session_state.email)
#     if details:
#         st.session_state.emp_id = details.get("employee_id")
#         st.session_state.grade = details.get("grade")
#         st.session_state.manager_id = details.get("manager_id")
#         st.session_state.first_name = details.get("first_name")

# emp_name_display = st.session_state.get("first_name") or st.session_state.email
# st.subheader(f"Welcome, {emp_name_display}! 👋")

# tab_upload, tab_claims = st.tabs(["📤 Upload Bill", "💼 Claims Dashboard"])
# with tab_upload:
#     extractor_node_ui(st.session_state.get("emp_id"), OUTPUT_DIR, input_dir)
# with tab_claims:
#     show_claims_dashboard()




# # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@



# employee_dashboard.py
import os
import re
import json
import time
from pathlib import Path
from datetime import date, datetime
import requests
import pandas as pd
import streamlit as st

import agent as _agent
import db_utils
from db_utils import save_expense_claim, log_validation_result, load_recent_claims
import utils as mail_utils

# -------------------------------------------------
# PAGE CONFIG (must be the first Streamlit call)
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

RECIPIENT_OVERRIDE = "kumar.vipin.official@gmail.com"

# -------------------------------------------------
# SESSION / NAV HELPERS
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
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return date.today()

def to_iso(d: date | str | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, str):
        return d
    return d.isoformat()

def deep_get(d, path, default=None):
    cur = d or {}
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

# -------------------------------------------------
# CLAIMS TABLE
# -------------------------------------------------
def show_claims_dashboard():
    st.caption("Showing your most recent claims")
    employee_id = st.session_state.get("emp_id")
    if not employee_id:
        st.warning("⚠️ Missing employee_id in session.")
        return
    try:
        df = load_recent_claims(employee_id, 50)
        if df is None or df.empty:
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
        return render_form_other(payload, emp_id)

# -------------------------------------------------
# EXTRACTOR UI
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
    if payload_out is None:
        return

    # validate
    try:
        r = requests.post(AGENT_ENDPOINT, params={"phase": "validate"}, json=payload_out, timeout=120)
        r.raise_for_status()
        validation_json = r.json() or {}
    except requests.exceptions.RequestException as e:
        validation_json = {"status": "ValidationError", "auto_approved": False, "error_msg": str(e)}

    # save claim
    try:
        tag_status = validation_json.get('tag', 'Pending')
        claim_id = save_expense_claim(payload_out, tag_status)
        st.success(f"✅ Expense Claim saved successfully! Claim ID: **{claim_id}**")
    except Exception as e:
        st.error(f"❌ Database insert failed: {e}")
        st.stop()

    # log validation (PASS THE DICT!)
    try:
        _ = log_validation_result(
            claim_id=claim_id,
            employee_id=payload_out.get("employee_id") or emp_id,
            validation_obj=validation_json,
        )
    except Exception as log_ex:
        st.warning(f"Validation log failed: {log_ex}")

    # ack email
    try:
        tag = validation_json.get("tag", "Pending")
        decision = validation_json.get("decision")
        comments = validation_json.get("comments") or deep_get(validation_json, "validation.message") or "No additional comments"
        employee_name = st.session_state.get("first_name")
        emp_id_for_email = payload_out.get("employee_id") or st.session_state.get("emp_id")
        category = (payload_out.get("category") or "other").title()
        amount = payload_out.get("total_amount", 0.0)
        currency = payload_out.get("currency", "INR")
        vendor = payload_out.get("vendor")
        expense_date = payload_out.get("expense_date")

        subject, content = mail_utils.draft_employee_ack_on_upload(
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
        sent = mail_utils.send_email(RECIPIENT_OVERRIDE, subject, content)
        if sent:
            st.success(f"📧 Acknowledgement sent to {RECIPIENT_OVERRIDE}")
        else:
            st.warning(f"Could not send email to {RECIPIENT_OVERRIDE}. Check SMTP credentials/connectivity.")
    except Exception as e:
        st.warning(f"Email step failed: {e}")

# -------------------------------------------------
# PAGE WIRING
# -------------------------------------------------
for key, default in {
    "ui_step": "idle",
    "extraction_resp": None,
    "extracted_payload": None,
    "uploaded_image_path": None,
    "last_payload": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

ensure_employee_allowed()

st.sidebar.write(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=do_logout_and_return)
if st.session_state.access_label == "M":
    st.sidebar.button("Manager View", on_click=go_manager)
if st.session_state.access_label == "F" or (st.session_state.get("email", "").lower() == "finance@company.com"):
    st.sidebar.button("Finance View", on_click=go_finance)

if not st.session_state.get("emp_id"):
    details = db_utils.load_employee_by_email(st.session_state.email)
    if details:
        st.session_state.emp_id = details.get("employee_id")
        st.session_state.grade = details.get("grade")
        st.session_state.manager_id = details.get("manager_id")
        st.session_state.first_name = details.get("first_name")

emp_name_display = st.session_state.get("first_name") or st.session_state.email
st.subheader(f"Welcome, {emp_name_display}! 👋")

tab_upload, tab_claims = st.tabs(["📤 Upload Bill", "💼 Claims Dashboard"])
with tab_upload:
    extractor_node_ui(st.session_state.get("emp_id"), OUTPUT_DIR, input_dir)
with tab_claims:
    show_claims_dashboard()
