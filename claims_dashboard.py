# claims_dashboard.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://myuser:rootpassword@localhost:5432/agent_max"
_engine = create_engine(DATABASE_URL, future=True)



def load_recent_claims(employee_id: str, limit: int = 50):
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), ec.employee_id) AS user_name,
            ec.expense_category AS claim_type,
            ec.amount,
            ec.currency,
            ec.status,
            ec.vendor_name AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        LEFT JOIN employees e ON e.employee_id = ec.employee_id
        WHERE ec.employee_id = %(emp_id)s
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
        LIMIT %(limit)s
    """
    with _engine.connect() as conn:
        return pd.read_sql_query(sql, conn, params={"emp_id": employee_id, "limit": int(limit)})


def show_claims_dashboard():
    st.title("💼 Expense Claims Dashboard")
    st.caption("Showing top 50 most recent claims")

    try:
        df = load_recent_claims(50)
        if df.empty:
            st.info("No claims found yet.")
        else:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "claim_id": "Claim ID",
                    "employee_id": "Employee ID",
                    "claim_type": "Claim Type",
                    "amount": st.column_config.NumberColumn(format="₹ %.2f"),
                    "currency": "Currency",
                    "status": "Status",
                    "vendor": "Vendor",
                    "claim_date": st.column_config.DatetimeColumn(format="YYYY-MM-DD")
                }
            )
    except Exception as e:
        st.error(f"Failed to load claims: {e}")
