import pandas as pd 
import database as _database
import datetime as dt

import json
import sqlalchemy as _sql 
from sqlalchemy import text


# --- Database connection (same as your agent_max setup) ---
DATABASE_URL = _database.DATABASE_URL
# Create engine
# engine = _database.engine
engine = _sql.create_engine(DATABASE_URL)

def get_employee_details(emp_id: str):
    query = f"SELECT * FROM employees WHERE employee_id = '{emp_id}';"
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df.to_dict(orient="records")


def get_expense_policy():
    query = f"SELECT * FROM expense_policies;"
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df.to_dict(orient="records")



def get_per_diem_rates(emp_id: str):
    query = f"SELECT * FROM per_diem_rates;"
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df.to_dict(orient="records")


def generate_claim_id():
    """Generate claim ID as CLM-YYYYMMDD-XXXX."""
    date_prefix = dt.datetime.now().strftime("%Y%m%d")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM expense_claims")).scalar() or 0
        next_num = result + 1
    return f"CLM-{date_prefix}-{next_num:04d}"



def save_expense_claim(payload: dict) -> str:
    """Insert claim record into expense_claims table."""
    claim_id = generate_claim_id()
    data = {
        "claim_id": claim_id,
        "employee_id": payload.get("employee_id"),
        "claim_date": payload.get("expense_date") or dt.date.today().isoformat(),
        "expense_category": payload.get("category", "misc"),
        "amount": payload.get("total_amount", 0.0),
        "currency": payload.get("currency", "INR"),
        "vendor_id": payload.get("vendor") or None,
        "linked_booking_id": payload.get("booking_details", {}).get("booking_number"),
        "receipt_id": payload.get("invoice_id"),
        "payment_mode": None,   # not in payload
        "status": "Pending Review",
        "Details": json.dumps(payload, indent=2),
        "Others_1": json.dumps(payload),
        "Others_2": None,
        "auto_approved": False,
        "is_duplicate": False,
        "fraud_flag": False,
    }

    insert_sql = text("""
        INSERT INTO expense_claims (
            claim_id, employee_id, claim_date, expense_category, amount, currency,
            vendor_id, linked_booking_id, receipt_id, payment_mode,
            status, Details, Others_1, Others_2,
            auto_approved, is_duplicate, fraud_flag
        )
        VALUES (
            :claim_id, :employee_id, :claim_date, :expense_category, :amount, :currency,
            :vendor_id, :linked_booking_id, :receipt_id, :payment_mode,
            :status, :Details, :Others_1, :Others_2,
            :auto_approved, :is_duplicate, :fraud_flag
        )
    """)

    with engine.begin() as conn:
        conn.execute(insert_sql, data)

    return claim_id