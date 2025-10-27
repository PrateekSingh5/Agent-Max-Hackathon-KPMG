

import streamlit as st
from typing import Optional, Dict, Any, List

# we no longer manage engine here
import db_utils  # <- this is your shared DB layer

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Company Login", layout="centered")


# -------------------------------------------------
# AUTH HELPERS
# -------------------------------------------------
def password_ok(input_password: str) -> bool:
    # simple rule for now
    return input_password == "password"

def can_access_employee_portal(user: Dict[str, Any]) -> bool:
    # Employee page allowed to E and M
    return user["access_label"] in {"E", "M"}

def can_access_manager_portal(user: Dict[str, Any]) -> bool:
    # Only managers
    return user["access_label"] == "M"

def can_access_finance_portal(user: Dict[str, Any]) -> bool:
    # Finance label F or shared finance email
    return (
        user["access_label"] == "F"
        or user["email"].lower() == "finance@company.com"
    )

def allowed_views_for_user(user: Dict[str, Any]) -> List[str]:
    views = []
    if can_access_employee_portal(user):
        views.append("Employee")
    if can_access_manager_portal(user):
        views.append("Manager")
    if can_access_finance_portal(user):
        views.append("Finance")
    return views


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
def init_session():
    defaults = {
        "logged_in": False,
        "email": None,
        "access_label": None,
        "allowed_views": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def set_login(user: Dict[str, Any]):
    st.session_state.logged_in = True
    st.session_state.email = user["email"]
    st.session_state.access_label = user["access_label"]
    st.session_state.allowed_views = allowed_views_for_user(user)

def logout():
    st.session_state.logged_in = False
    st.session_state.email = None
    st.session_state.access_label = None
    st.session_state.allowed_views = []


# -------------------------------------------------
# LOGIN FORMS
# -------------------------------------------------
def login_form(form_key: str, portal_label: str):
    """
    form_key: "emp" | "mgr" | "fin"
    portal_label: just UI text
    """
    with st.form(key=form_key + "_form"):
        st.write(f"{portal_label} Portal Login")
        email = st.text_input("Email", key=form_key + "_email")
        pwd = st.text_input("Password", type="password", key=form_key + "_pwd")
        submit = st.form_submit_button("Login")
    return email, pwd, submit


def complete_login_and_redirect(user: Dict[str, Any]):
    """
    Save session, then push to the correct dashboard page.
    We'll pick the 'highest' view user can access:
    Manager > Finance > Employee
    """
    set_login(user)

    if can_access_manager_portal(user):
        st.switch_page("pages/manager_dashboard.py")

    elif can_access_finance_portal(user):
        st.switch_page("pages/finance_dashboard.py")

    elif can_access_employee_portal(user):
        st.switch_page("pages/employee_dashboard.py")

    else:
        st.error("You logged in but you have no dashboard permission.")


def process_login_attempt(email: str, pwd: str, portal_type: str):
    """
    portal_type: "emp" | "mgr" | "fin"
    We verify:
    - user exists
    - password
    - portal access
    Then redirect.
    """
    user = db_utils.fetch_user_by_email(email)  # <--- now using db_utils
    if user is None:
        st.error("User not found")
        return
    if not password_ok(pwd):
        st.error("Invalid password")
        return

    if portal_type == "emp":
        if not can_access_employee_portal(user):
            st.error("Access denied for Employee portal")
            return
    elif portal_type == "mgr":
        if not can_access_manager_portal(user):
            st.error("Access denied. Manager only.")
            return
    elif portal_type == "fin":
        if not can_access_finance_portal(user):
            st.error("Access denied. Finance only.")
            return

    # good login
    complete_login_and_redirect(user)


# -------------------------------------------------
# WHEN LOGGED OUT: SHOW 3 TABS
# -------------------------------------------------
def render_logged_out_tabs():
    tabs = st.tabs(["Employee", "Manager", "Finance"])

    with tabs[0]:
        email, pwd, submit = login_form("emp", "Employee")
        if submit:
            process_login_attempt(email, pwd, "emp")

    with tabs[1]:
        email, pwd, submit = login_form("mgr", "Manager")
        if submit:
            process_login_attempt(email, pwd, "mgr")

    with tabs[2]:
        email, pwd, submit = login_form("fin", "Finance")
        if submit:
            process_login_attempt(email, pwd, "fin")


# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    init_session()

    st.title("Company Portal")

    if st.session_state.logged_in:
        st.caption(
            f"Logged in as {st.session_state.email} "
            f"(role: {st.session_state.access_label})"
        )

        # User refreshed login page after logging in → send them again
        fake_user = {
            "email": st.session_state.email,
            "access_label": st.session_state.access_label,
        }
        complete_login_and_redirect(fake_user)
        st.stop()

    else:
        st.info("Please log in:")
        render_logged_out_tabs()


if __name__ == "__main__":
    main()
