import streamlit as st
import db_utils
import agent as _agent  # for load_employee_by_email


try:
    import db_utils as db_utils   # if your file is named du_utils.py
except ImportError:
    import db_utils               # else fallback to db_utils.py

# For executing SQL in the fallback path
from sqlalchemy import text

# (Optional) typing hints
from typing import List, Dict
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
            st.switch_page("portal_login.py")
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





def _finance_update_claim_fallback(claim_id: str, decision: str, comment: str, approver_id: str):
    """
    Fallback direct-SQL updater if db_utils.finance_update_claim_decision(...) is not available.
    Uses db_utils.engine. Stores only status by default; enable comment/approver columns if present.
    """
    sql_basic = text("""
        UPDATE expense_claims
        SET status = :status
        WHERE claim_id = :claim_id
    """)
    # If your schema has finance_comment and finance_approver_id columns, switch to:
    # sql_with_comment = text("""
    #   UPDATE expense_claims
    #   SET status = :status,
    #       finance_comment = :comment,
    #       finance_approver_id = :fid
    #   WHERE claim_id = :claim_id
    # """)

    with db_utils.engine.begin() as conn:
        conn.execute(sql_basic, {
            "status": "Approved" if decision == "Approve" else "Rejected",
            "claim_id": claim_id,
            # "comment": comment,
            # "fid": approver_id,
        })

def _apply_finance_decisions(rows_to_apply: list[dict], approver_id: str):
    updater = getattr(db_utils, "finance_update_claim_decision", None)
    successes, failures = [], []
    for r in rows_to_apply:
        claim_id = str(r.get("claim_id", "")).strip()
        decision = str(r.get("Decision", "")).strip()
        comment  = str(r.get("Finance Comment", "")).strip()
        if not claim_id or decision not in {"Approve", "Reject"}:
            continue
        try:
            if callable(updater):
                updater(claim_id, decision, comment, approver_id)
            else:
                _finance_update_claim_fallback(claim_id, decision, comment, approver_id)
            successes.append(claim_id)
        except Exception as ex:
            failures.append((claim_id, str(ex)))
    return successes, failures

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
    if not _is_finance_user():
        st.warning("You do not have finance approval rights.")
        return

    # Resolve finance approver id (employee id in session)
    fin_emp_id = st.session_state.get("emp_id", "") or ""

    try:
        df = db_utils.load_finance_pending_claims()
        if df is None or df.empty:
            st.info("No claims are pending with Finance at the moment.")
            return

        work = df.copy()

        # Add editable columns if not present
        if "Decision" not in work.columns:
            work["Decision"] = ""
        if "Finance Comment" not in work.columns:
            work["Finance Comment"] = ""

        st.markdown("### Pending Claims (Finance Review)")
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
                # Editable:
                "Decision": st.column_config.SelectboxColumn(
                    "Decision",
                    options=["", "Approve", "Reject"],
                    required=False,
                    help="Choose Approve or Reject for each claim you want to act on."
                ),
                "Finance Comment": st.column_config.TextColumn(
                    "Finance Comment",
                    help="Optional note stored with your decision."
                ),
            },
            disabled=[
                "claim_id", "employee_id", "user_name", "claim_type",
                "amount", "currency", "status", "vendor_name", "claim_date"
            ],
            key="finance_editor",
        )

        c1, c2 = st.columns([1, 3])
        with c1:
            do_submit = st.button("Submit decisions", use_container_width=True, key="finance_submit_btn")
        with c2:
            st.caption("Tip: leave Decision blank to skip a row.")

        if do_submit:
            rows = edited.fillna("").to_dict(orient="records")
            to_apply = [r for r in rows if r.get("Decision") in {"Approve", "Reject"}]

            if not to_apply:
                st.info("No decisions to apply.")
                return

            ok, bad = _apply_finance_decisions(to_apply, approver_id=fin_emp_id)

            if ok:
                st.success(f"Updated {len(ok)} claim(s): {', '.join(ok)}")
            if bad:
                st.error("Some updates failed:")
                for cid, msg in bad:
                    st.write(f"- {cid}: {msg}")

            # Refresh UI by removing processed rows locally
            if ok:
                remaining = edited[~edited["claim_id"].isin(ok)].drop(columns=["Decision", "Finance Comment"], errors="ignore")
                if remaining.empty:
                    st.info("All finance pending items are processed. 🎉")
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
        st.error(f"Failed to load finance pending claims: {e}")

with tab_review:
    finance_approve()
