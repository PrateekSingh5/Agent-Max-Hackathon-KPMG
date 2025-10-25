# import pandas as pd 
# import database as _database
# import datetime as dt
# from datetime import datetime
# import json
# import sqlalchemy as _sql 
# from sqlalchemy import text


# # --- Database connection (same as your agent_max setup) ---
# DATABASE_URL = _database.DATABASE_URL
# # Create engine
# # engine = _database.engine
# engine = _sql.create_engine(DATABASE_URL)

# def get_employee_details(emp_id: str):
#     query = f"SELECT * FROM employees WHERE employee_id = '{emp_id}';"
#     with engine.connect() as conn:
#         df = pd.read_sql_query(query, conn)
#     return df.to_dict(orient="records")


# def get_expense_policy():
#     query = f"SELECT * FROM expense_policies;"
#     with engine.connect() as conn:
#         df = pd.read_sql_query(query, conn)
#     return df.to_dict(orient="records")


# def get_per_diem_rates(emp_id: str):
#     query = f"SELECT * FROM per_diem_rates;"
#     with engine.connect() as conn:
#         df = pd.read_sql_query(query, conn)
#     return df.to_dict(orient="records")


# def generate_claim_id():
#     """Generate claim ID as CLM-YYYYMMDD-XXXX."""
#     date_prefix = dt.datetime.now().strftime("%Y%m%d")
#     with engine.connect() as conn:
#         result = conn.execute(text("SELECT COUNT(*) FROM expense_claims")).scalar() or 0
#         next_num = result + 1
#     return f"CLM-{date_prefix}-{next_num:04d}"


# def save_expense_claim(payload_out: dict) -> str:
#     """
#     Insert one row into expense_claims using the normalized payload
#     coming from Streamlit (hotel/travel/food/local_conveyance/other).

#     Returns the generated claim_id.
#     """

#     # 1. Generate claim_id
#     now = datetime.now()
#     claim_id = f"CLM-{now.strftime('%Y%m%d-%H%M%S')}"

#     # 2. Basic fields from payload_out
#     employee_id = payload_out.get("employee_id")
#     expense_category = payload_out.get("category", "other")
#     amount = float(payload_out.get("total_amount", 0.0) or 0.0)
#     currency = payload_out.get("currency", "INR")

#     raw_vendor = payload_out.get("vendor") or ""
#     vendor_name = raw_vendor or None  # can be long now, varchar(255)

#     # receipt / invoice reference
#     receipt_id = (
#         payload_out.get("invoice_id")
#         or payload_out.get("invoice_number")
#         or None
#     )

#     # claim_date (we treat this as the "expense_date" in payload)
#     claim_date = payload_out.get("expense_date")
#     if isinstance(claim_date, str):
#         # already "YYYY-MM-DD"
#         db_claim_date = claim_date
#     else:
#         # fallback to "today"
#         db_claim_date = now.strftime("%Y-%m-%d")

#     # We don't yet collect these from the form, so leave them None
#     linked_booking_id = None
#     payment_mode = None

#     status_val = "Pending Review"

#     # 3. Build Details and Others_1 JSON blobs for auditing/review
#     details_obj = {
#         "invoice_id": payload_out.get("invoice_id"),
#         "employee_id": employee_id,
#         "expense_date": payload_out.get("expense_date"),
#         "vendor": raw_vendor,
#         "total_amount": amount,
#         "currency": currency,
#         "category": expense_category,

#         # structured blocks
#         "travel_block": payload_out.get("travel_block"),
#         "booking_details": payload_out.get("booking_details"),
#         "food_details": payload_out.get("food_details"),
#         "other_details": payload_out.get("other_details"),
#     }

#     Details = json.dumps(details_obj, indent=2, default=str)

#     # full raw payload snapshot
#     Others_1 = json.dumps(payload_out, default=str)
#     Others_2 = None

#     auto_approved = False
#     is_duplicate = False
#     fraud_flag = False

#     insert_sql = text("""
#         INSERT INTO expense_claims (
#             claim_id,
#             employee_id,
#             claim_date,
#             expense_category,
#             amount,
#             currency,
#             vendor_name,
#             linked_booking_id,
#             receipt_id,
#             payment_mode,
#             status,
#             Details,
#             Others_1,
#             Others_2,
#             auto_approved,
#             is_duplicate,
#             fraud_flag
#         )
#         VALUES (
#             :claim_id,
#             :employee_id,
#             :claim_date,
#             :expense_category,
#             :amount,
#             :currency,
#             :vendor_name,
#             :linked_booking_id,
#             :receipt_id,
#             :payment_mode,
#             :status,
#             :Details,
#             :Others_1,
#             :Others_2,
#             :auto_approved,
#             :is_duplicate,
#             :fraud_flag
#         )
#     """)

#     with engine.begin() as conn:
#         conn.execute(
#             insert_sql,
#             {
#                 "claim_id": claim_id,
#                 "employee_id": employee_id,
#                 "claim_date": db_claim_date,
#                 "expense_category": expense_category,
#                 "amount": amount,
#                 "currency": currency,
#                 "vendor_name": vendor_name,
#                 "linked_booking_id": linked_booking_id,
#                 "receipt_id": receipt_id,
#                 "payment_mode": payment_mode,
#                 "status": status_val,
#                 "Details": Details,
#                 "Others_1": Others_1,
#                 "Others_2": Others_2,
#                 "auto_approved": auto_approved,
#                 "is_duplicate": is_duplicate,
#                 "fraud_flag": fraud_flag,
#             },
#         )

#     return claim_id


# def load_manager_pending_claims(manager_id: str, limit: int = 100):
#     """
#     For managers:
#     Show all PENDING REVIEW claims for direct reports.
#     Direct report = employees.manager_id == this manager's employee_id.
#     """
#     sql = """
#         SELECT
#             ec.claim_id,
#             ec.employee_id,
#             COALESCE(
#                 NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''),
#                 ec.employee_id
#             ) AS user_name,
#             ec.expense_category AS claim_type,
#             ec.amount,
#             ec.currency,
#             ec.status,
#             ec.vendor_id AS vendor_name,
#             ec.claim_date
#         FROM expense_claims ec
#         INNER JOIN employees e
#             ON e.employee_id = ec.employee_id
#         WHERE
#             e.manager_id = %(mgr_id)s
#             AND ec.status = 'Pending Review'
#         ORDER BY ec.claim_date DESC, ec.claim_id DESC
#         LIMIT %(limit_val)s
#     """

#     with engine.connect() as conn:
#         df = pd.read_sql_query(
#             sql,
#             conn,
#             params={
#                 "mgr_id": manager_id,
#                 "limit_val": int(limit),
#             },
#         )

#     return df



# db_utils.py
import pandas as pd
import database as _database
import datetime as dt
from datetime import datetime
import json
import sqlalchemy as _sql
from sqlalchemy import text

# --- Database connection (same as your agent_max setup) ---
DATABASE_URL = _database.DATABASE_URL
engine = _sql.create_engine(DATABASE_URL, future=True)


# ----------------------------
# Small internal helpers
# ----------------------------
def _empty_df(columns=None):
    return pd.DataFrame(columns=columns or [])

def _safe_read_sql(sql: str, params: dict | None = None):
    """
    Run a SELECT safely. Returns (df, err) where err is None on success.
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params or {})
        return df, None
    except Exception as ex:
        # You can replace print with your logger
        print(f"[db_utils] SQL error: {ex}")
        return _empty_df(), ex


# ----------------------------
# Existing functions (tightened)
# ----------------------------
def get_employee_details(emp_id: str):
    sql = """
        SELECT *
        FROM employees
        WHERE employee_id = %(emp_id)s
        LIMIT 1
    """
    df, err = _safe_read_sql(sql, {"emp_id": emp_id})
    if err:
        return []
    return df.to_dict(orient="records")


def get_expense_policy():
    sql = "SELECT * FROM expense_policies;"
    df, err = _safe_read_sql(sql)
    if err:
        return []
    return df.to_dict(orient="records")


def get_per_diem_rates(emp_id: str | None = None):
    # Keeping signature you had, but emp_id is unused in your query
    sql = "SELECT * FROM per_diem_rates;"
    df, err = _safe_read_sql(sql)
    if err:
        return []
    return df.to_dict(orient="records")


def generate_claim_id():
    """Generate claim ID as CLM-YYYYMMDD-XXXX."""
    date_prefix = dt.datetime.now().strftime("%Y%m%d")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM expense_claims")).scalar() or 0
            next_num = int(result) + 1
    except Exception as ex:
        print(f"[db_utils] generate_claim_id error: {ex}")
        next_num = 1
    return f"CLM-{date_prefix}-{next_num:04d}"


def save_expense_claim(payload_out: dict) -> str:
    """
    Insert one row into expense_claims using the normalized payload
    coming from Streamlit (hotel/travel/food/local_conveyance/other).
    Returns the generated claim_id.
    """
    now = datetime.now()
    claim_id = f"CLM-{now.strftime('%Y%m%d-%H%M%S')}"

    employee_id = payload_out.get("employee_id")
    expense_category = payload_out.get("category", "other")
    amount = float(payload_out.get("total_amount", 0.0) or 0.0)
    currency = payload_out.get("currency", "INR")

    raw_vendor = payload_out.get("vendor") or ""
    vendor_name = raw_vendor or None

    receipt_id = (
        payload_out.get("invoice_id")
        or payload_out.get("invoice_number")
        or None
    )

    claim_date = payload_out.get("expense_date")
    if isinstance(claim_date, str) and claim_date:
        db_claim_date = claim_date
    else:
        db_claim_date = now.strftime("%Y-%m-%d")

    linked_booking_id = None
    payment_mode = None
    status_val = "Pending Review"

    details_obj = {
        "invoice_id": payload_out.get("invoice_id"),
        "employee_id": employee_id,
        "expense_date": payload_out.get("expense_date"),
        "vendor": raw_vendor,
        "total_amount": amount,
        "currency": currency,
        "category": expense_category,
        "travel_block": payload_out.get("travel_block"),
        "booking_details": payload_out.get("booking_details"),
        "food_details": payload_out.get("food_details"),
        "other_details": payload_out.get("other_details"),
    }
    Details = json.dumps(details_obj, indent=2, default=str)
    Others_1 = json.dumps(payload_out, default=str)
    Others_2 = None

    auto_approved = False
    is_duplicate = False
    fraud_flag = False

    insert_sql = text("""
        INSERT INTO expense_claims (
            claim_id,
            employee_id,
            claim_date,
            expense_category,
            amount,
            currency,
            vendor_name,
            linked_booking_id,
            receipt_id,
            payment_mode,
            status,
            Details,
            Others_1,
            Others_2,
            auto_approved,
            is_duplicate,
            fraud_flag
        )
        VALUES (
            :claim_id,
            :employee_id,
            :claim_date,
            :expense_category,
            :amount,
            :currency,
            :vendor_name,
            :linked_booking_id,
            :receipt_id,
            :payment_mode,
            :status,
            :Details,
            :Others_1,
            :Others_2,
            :auto_approved,
            :is_duplicate,
            :fraud_flag
        )
    """)

    try:
        with engine.begin() as conn:
            conn.execute(
                insert_sql,
                {
                    "claim_id": claim_id,
                    "employee_id": employee_id,
                    "claim_date": db_claim_date,
                    "expense_category": expense_category,
                    "amount": amount,
                    "currency": currency,
                    "vendor_name": vendor_name,
                    "linked_booking_id": linked_booking_id,
                    "receipt_id": receipt_id,
                    "payment_mode": payment_mode,
                    "status": status_val,
                    "Details": Details,
                    "Others_1": Others_1,
                    "Others_2": Others_2,
                    "auto_approved": auto_approved,
                    "is_duplicate": is_duplicate,
                    "fraud_flag": fraud_flag,
                },
            )
    except Exception as ex:
        print(f"[db_utils] save_expense_claim error: {ex}")
        # Re-raise or return a sentinel; returning ID keeps UI simple
        # but your caller might want to handle failure separately.
        # raise
    return claim_id


# ----------------------------
# NEW / UPDATED QUERIES
# ----------------------------

def load_recent_claims(emp_id: str, limit: int = 50) -> pd.DataFrame:
    """
    Employee self-view: latest claims for a given employee.
    Fixes previous error by NOT using ec.vendor_id.
    """
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(
                NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''),
                ec.employee_id
            ) AS user_name,
            ec.expense_category AS claim_type,
            ec.amount,
            ec.currency,
            ec.status,
            COALESCE(ec.vendor_name, ec.details->>'vendor') AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        LEFT JOIN employees e
            ON e.employee_id = ec.employee_id
        WHERE ec.employee_id = %(emp_id)s
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
        LIMIT %(limit)s
    """
    df, err = _safe_read_sql(sql, {"emp_id": emp_id, "limit": int(limit)})
    if err:
        # Return empty DF with expected columns to avoid UI crashes
        return _empty_df([
            "claim_id", "employee_id", "user_name", "claim_type",
            "amount", "currency", "status", "vendor_name", "claim_date"
        ])
    return df


def load_manager_pending_claims(manager_id: str, limit: int = 100) -> pd.DataFrame:
    """
    Managers: show all 'Pending Review' claims for direct reports.
    Fixes previous error by using vendor_name/JSON instead of vendor_id.
    """
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(
                NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''),
                ec.employee_id
            ) AS user_name,
            ec.expense_category AS claim_type,
            ec.amount,
            ec.currency,
            ec.status,
            COALESCE(ec.vendor_name, ec.details->>'vendor') AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        INNER JOIN employees e
            ON e.employee_id = ec.employee_id
        WHERE
            e.manager_id = %(mgr_id)s
            AND ec.status = 'Pending Review'
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
        LIMIT %(limit_val)s
    """
    df, err = _safe_read_sql(sql, {"mgr_id": manager_id, "limit_val": int(limit)})
    if err:
        return _empty_df([
            "claim_id", "employee_id", "user_name", "claim_type",
            "amount", "currency", "status", "vendor_name", "claim_date"
        ])
    return df


def load_finance_pending_claims(limit: int = 200) -> pd.DataFrame:
    """
    Finance view: list all claims waiting for finance (adjust status as per your workflow).
    For example, include both 'Pending Review' and 'Manager Approved'.
    """
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(
                NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''),
                ec.employee_id
            ) AS user_name,
            ec.expense_category AS claim_type,
            ec.amount,
            ec.currency,
            ec.status,
            COALESCE(ec.vendor_name, ec.details->>'vendor') AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        LEFT JOIN employees e
            ON e.employee_id = ec.employee_id
        WHERE ec.status IN ('Pending Review', 'Manager Approved')
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
        LIMIT %(limit_val)s
    """
    df, err = _safe_read_sql(sql, {"limit_val": int(limit)})
    if err:
        return _empty_df([
            "claim_id", "employee_id", "user_name", "claim_type",
            "amount", "currency", "status", "vendor_name", "claim_date"
        ])
    return df
