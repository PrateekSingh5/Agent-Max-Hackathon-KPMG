import streamlit as st
import db_utils
import agent as _agent  # for load_employee_by_email

# -------------------------------------------------
# PAGE CONFIG (must be first Streamlit call)
# -------------------------------------------------
st.set_page_config(page_title="Finance Dashboard", layout="wide")

# -------------------------------------------------
# SESSION / NAV HELPERS
# -------------------------------------------------
def do_logout_and_return():
    # mirror logout in test_portal_login.py
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.access_label = None
    st.session_state.allowed_views = []
    st.switch_page("test_portal_login.py")

def go_employee():
    st.switch_page("pages/manager_dashboard.py")  # employee dashboard is currently manager_dashboard.py in your codebase

def go_manager():
    st.switch_page("pages/manager_dashboard.py")

def go_finance():
    st.switch_page("pages/finance_dashboard.py")

def ensure_finance_allowed():
    """
    Must be:
    - logged in
    AND
    - access_label == "F" OR email == finance@company.com
    Otherwise: stop.
    """
    if not st.session_state.get("logged_in", False):
        st.error("Please login first.")
        if st.button("Go to Login"):
            st.switch_page("test_portal_login.py")
        st.stop()

    access_label = st.session_state.get("access_label", "")
    email_lower = st.session_state.get("email", "").lower()

    if not (
        access_label == "F"
        or email_lower == "finance@company.com"
    ):
        st.error("Access denied. Finance portal only.")
        st.sidebar.button("Logout", on_click=do_logout_and_return)
        st.stop()

# -------------------------------------------------
# FINANCE TAB: PENDING CLAIMS
# -------------------------------------------------
def finance_pending_claims_ui():
    st.header("🏦 Finance Review Queue")

    # make sure we know who is 'finance reviewer'
    reviewer_emp_id = st.session_state.get("emp_id")

    if not reviewer_emp_id:
        st.warning("Could not resolve your employee_id from session. Trying to fetch…")

        # same pattern you used elsewhere to populate emp_id for logged-in user
        details = _agent.load_employee_by_email(st.session_state.email)
        if details:
            st.session_state.emp_id = details.get("employee_id")
            st.session_state.grade = details.get("grade")
            st.session_state.manager_id = details.get("manager_id")
            st.session_state.first_name = details.get("first_name")

        reviewer_emp_id = st.session_state.get("emp_id")

    # if still no emp_id, bail out
    if not reviewer_emp_id:
        st.error("Still missing employee_id. Please re-login.")
        return

    st.caption(
        "Below are expense claims awaiting finance action. "
        "For now we're reusing the manager pending-claims loader."
    )

    try:
        # NOTE: we're temporarily calling the manager-based loader
        pending_df = db_utils.load_manager_pending_claims(
            manager_id=reviewer_emp_id,
            limit=200
        )

        if pending_df is None or pending_df.empty:
            st.info("✅ No pending claims for you right now.")
            return

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
        st.error(f"Failed to load finance review claims: {e}")

# -------------------------------------------------
# PAGE RENDER
# -------------------------------------------------

# 1. Gate access
ensure_finance_allowed()

# 2. Sidebar: who am I / nav
st.sidebar.write(f"Logged in as {st.session_state.email}")
st.sidebar.button("Logout", on_click=do_logout_and_return)

# Optional cross-nav buttons depending on role
if st.session_state.access_label in {"E", "M"}:
    st.sidebar.button("Employee / Manager View", on_click=go_manager)

if st.session_state.access_label == "M":
    st.sidebar.button("Manager View", on_click=go_manager)

if (
    st.session_state.access_label == "F"
    or st.session_state.get("email", "").lower() == "finance@company.com"
):
    st.sidebar.button("Finance View", on_click=go_finance, disabled=True)

# 3. Resolve display name
if not st.session_state.get("emp_id"):
    details = _agent.load_employee_by_email(st.session_state.email)
    if details:
        st.session_state.emp_id = details.get("employee_id")
        st.session_state.grade = details.get("grade")
        st.session_state.manager_id = details.get("manager_id")
        st.session_state.first_name = details.get("first_name")

display_name = (
    st.session_state.get("first_name")
    or st.session_state.get("email")
    or "Finance User"
)

st.subheader(f"Welcome, {display_name}! 🧾")

# 4. Tabs (Finance will mostly care about review/settlement/etc.)
Dashboard, tab_review, = st.tabs(["Dashboard","Pending Claims Review"])

with Dashboard:
    st.write("Dashbaoard")

with tab_review:
    finance_pending_claims_ui()

