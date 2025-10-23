# claims_dashboard.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://myuser:rootpassword@localhost:5432/agent_max"
engine = create_engine(DATABASE_URL, future=True)

def load_recent_claims(limit=50):
    query = f"""
        SELECT claim_id, employee_id, expense_category AS claim_type,
               amount, currency, status, vendor_id AS vendor,
               claim_date
        FROM expense_claims
        ORDER BY claim_date DESC
        LIMIT {limit};
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df

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
