import streamlit as st
import db_utils
import agent as _agent  # for load_employee_by_email

# -------------------------------------------------
# PAGE CONFIG (must be first Streamlit call)
# -------------------------------------------------
st.set_page_config(page_title="Finance Dashboard", layout="wide")

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
FINANCE_EMAILS = {
    "financ.team@company.com",
    "finance.tech@company.com"
}

def _is_finance_user() -> bool:
    """Single source of truth for Finance authorization."""
    access_label = (st.session_state.get("access_label") or "").upper()
    email_lower = (st.session_state.get("email") or "").lower()
    dept_lower = (st.session_state.get("department") or "").lower()

    if access_label == "F":
        return True
    if email_lower in FINANCE_EMAILS:
        return True
    if dept_lower == "finance":
        return True
    return False

# -------------------------------------------------
# SESSION / NAV HELPERS
# -------------------------------------------------
def do_logout_and_return():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.access_label = None
    st.session_state.allowed_views = []
    st.switch_page("portal_login.py")

def go_employee():
    st.switch_page("pages/manager_dashboard.py")  # your “employee” view

def go_manager():
    st.switch_page("pages/manager_dashboard.py")

def go_finance():
    st.switch_page("pages/finance_dashboard.py")

def ensure_finance_allowed():
    """
    Must be logged in AND recognized as Finance (label/email/department).
    """
    if not st.session_state.get("logged_in", False):
        st.error("Please login first.")
        if st.button("Go to Login"):
            st.switch_page("test_portal_login.py")
        st.stop()

    # --- Promote access_label to F if their employee record says Finance ---
    if not st.session_state.get("emp_id"):
        details = _agent.load_employee_by_email(st.session_state.get("email", ""))
        if details:
            # `details` can be dict or list; normalize to dict
            if isinstance(details, list) and details:
                details = details[0]
            st.session_state.emp_id = details.get("employee_id")
            st.session_state.grade = details.get("grade")
            st.session_state.manager_id = details.get("manager_id")
            st.session_state.first_name = details.get("first_name")
            st.session_state.department = details.get("department")

            # If dept=Finance but label isn't F, upgrade it
            if (details.get("department", "") or "").lower() == "finance":
                st.session_state.access_label = "F"

    # If still not recognized as Finance, fall back to email whitelisting
    if not _is_finance_user():
        st.error("Access denied. Finance portal only.")
        st.sidebar.button("Logout", on_click=do_logout_and_return)
        st.stop()

# -------------------------------------------------
# PAGE RENDER
# -------------------------------------------------

# 1) Gate access
ensure_finance_allowed()

# 2) Sidebar: who am I / nav
st.sidebar.write(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=do_logout_and_return)

# Optional cross-nav buttons depending on role
if st.session_state.access_label in {"E", "M"}:
    st.sidebar.button("Employee / Manager View", on_click=go_manager)

if st.session_state.access_label == "M":
    st.sidebar.button("Manager View", on_click=go_manager)

# Finance users will see Finance View disabled (you’re already here)
st.sidebar.button("Finance View", on_click=go_finance, disabled=True)

# 3) Resolve display name
display_name = (
    st.session_state.get("first_name")
    or st.session_state.get("email")
    or "Finance User"
)

st.subheader(f"Welcome, {display_name}! 🧾")

# 4) Tabs
Dashboard, tab_review = st.tabs(["Dashboard", "Pending Claims Review"])

with Dashboard:
    st.write("Dashboard")

def finance_approve():
    """
    Show ALL claims routed to Finance (status = 'Finance Pending').
    """
    # --- Use unified check here too ---
    if not _is_finance_user():
        # (Fixes your incorrect message string: this is FINANCE rights, not MANAGER)
        st.warning("You do not have finance approval rights.")
        return

    try:
        df = db_utils.load_finance_pending_claims()

        if df is None or df.empty:
            st.info("No claims are pending with Finance at the moment.")
            return

        st.dataframe(
            df,
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
                "claim_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
            },
        )
    except Exception as e:
        st.error(f"Failed to load finance pending claims: {e}")

with tab_review:
    finance_approve()
