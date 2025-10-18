
import database as _database

import sqlalchemy as _sql
import pandas as pd

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

