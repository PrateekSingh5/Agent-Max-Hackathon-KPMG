
# db_utils.py
import pandas as pd
import database as _database
import datetime as dt
from datetime import datetime
import json
import sqlalchemy as _sql
from sqlalchemy import text

from typing import Optional, List
import pandas as pd

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

def save_expense_claim(payload_out: dict, status) -> str:
    """
    Insert one row into expense_claims using the normalized payload
    coming from Streamlit (hotel/travel/food/local_conveyance/other).
    'tag' determines the initial status and auto_approved if applicable.
    Returns the generated claim_id.
    """
    now = datetime.now()
    claim_id = f"CLM-{now.strftime('%Y%m%d-%H%M%S')}"

    # ---- base fields from payload ----
    employee_id = payload_out.get("employee_id")
    expense_category = payload_out.get("category", "other")
    amount = float(payload_out.get("total_amount", 0.0) or 0.0)
    currency = payload_out.get("currency", "INR")
    raw_vendor = (payload_out.get("vendor") or "").strip()
    vendor_name = raw_vendor or None
    receipt_id = payload_out.get("invoice_id") or payload_out.get("invoice_number") or None

    claim_date = payload_out.get("expense_date")
    if isinstance(claim_date, str) and claim_date:
        db_claim_date = claim_date
    else:
        db_claim_date = now.strftime("%Y-%m-%d")

    # ---- normalize tag -> status & auto_approved & payment_mode ----
    status_val = status
    auto_approved_flag = False
    payment_mode = payload_out.get("payment_mode") or None

    if isinstance(status, dict):
        status_val = (
            status.get("status")
            or status.get("route_status")
            or status.get("final_status")
            or "Pending Review"
        )
        auto_approved_flag = bool(status.get("auto_approved", False))
        if status.get("payment_mode") and not payment_mode:
            payment_mode = status.get("payment_mode")
    elif isinstance(status, str):
        status_val = status  # e.g. "Auto Approved", "Pending Review", etc.

    # ---- optional fields (kept as None) ----
    linked_booking_id = None

    # ---- build Details / Others_1 safely (truncate if your columns are VARCHAR) ----
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
        "payment_mode": payment_mode,              # copy for audit
        "status_from_tag": status_val,             # normalized status
        "auto_approved_from_tag": auto_approved_flag,
        "raw_tag": "",                            # keep full tag for traceability
    }

    # If your table columns are TEXT you can skip truncation. If they are VARCHAR(n),
    # adjust these limits to your column sizes to avoid Postgres string truncation errors.
    def _to_json_truncated(obj, max_len: int):
        s = json.dumps(obj, ensure_ascii=False, default=str)
        return s if len(s) <= max_len else (s[: max_len - 3] + "...")

    # Conservative caps; tweak if you know your exact VARCHAR sizes
    DETAILS_MAX = 4000
    OTHERS1_MAX = 4000

    Details = _to_json_truncated(details_obj, DETAILS_MAX)
    Others_1 = _to_json_truncated(payload_out, OTHERS1_MAX)
    Others_2 = None

    # ---- final insert (never send None for boolean) ----
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
                    "auto_approved": bool(auto_approved_flag),  # ← always boolean
                    "is_duplicate": False,
                    "fraud_flag": False,
                },
            )
    except Exception as ex:
        print(f"[db_utils] save_expense_claim error: {ex}")
        raise
    return claim_id


def log_validation_result(claim_id: str, employee_id: str, validation_obj: dict):
    """
    Store validator decision snapshot in expense_validation_logs.
    validation_obj is the JSON returned by the policy validation agent.
    Expected keys we care about:
      - "status" / "route_status" / "final_status"    -> mapped to status_val
      - "payment_mode"
      - "auto_approved" (bool)
    We'll keep the full blob in raw_validation_json.
    """

    # --- defensive fetches ---
    status_val = (
        validation_obj.get("status")
        or validation_obj.get("route_status")
        or validation_obj.get("final_status")
        or "Pending Review"
    )

    payment_mode = validation_obj.get("payment_mode")
    auto_approved = bool(validation_obj.get("auto_approved", False))

    insert_sql = text("""
        INSERT INTO expense_validation_logs (
            claim_id,
            employee_id,
            status_val,
            payment_mode,
            auto_approved,
            raw_validation_json
        )
        VALUES (
            :claim_id,
            :employee_id,
            :status_val,
            :payment_mode,
            :auto_approved,
            :raw_validation_json
        )
    """)

    with engine.begin() as conn:
        conn.execute(
            insert_sql,
            {
                "claim_id": claim_id,
                "employee_id": employee_id,
                "status_val": status_val,
                "payment_mode": payment_mode,
                "auto_approved": auto_approved,
                "raw_validation_json": json.dumps(validation_obj, default=str),
            },
        )

    # return what we actually wrote, could help UI
    return {
        "claim_id": claim_id,
        "status_val": status_val,
        "payment_mode": payment_mode,
        "auto_approved": auto_approved,
    }

def update_claim_status(claim_id: str, status_val: str, auto_approved: bool):
    upd_sql = text("""
        UPDATE expense_claims
        SET status = :status_val,
            auto_approved = :auto_approved
        WHERE claim_id = :claim_id
    """)
    with engine.begin() as conn:
        conn.execute(
            upd_sql,
            {
                "claim_id": claim_id,
                "status_val": status_val,
                "auto_approved": auto_approved,
            },
        )

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

def manager_update_claim_decision(claim_id: str, decision: str, comment: str, approver_id: str) -> None:
    """
    decision: 'Approve' or 'Reject'
    Updates expense_claims.status and stores manager comment if supported by your schema.
    """
    status_val = "Approved" if decision == "Approve" else "Rejected"
    with engine.begin() as conn:
        # If you have manager_comment + manager_id columns:
        # conn.execute(text("""
        #     UPDATE expense_claims
        #     SET status = :status,
        #         manager_comment = :comment,
        #         manager_id = :mgr_id
        #     WHERE claim_id = :claim_id
        # """), {"status": status_val, "comment": comment, "mgr_id": approver_id, "claim_id": claim_id})

        # Minimal version: update only status
        conn.execute(text("""
            UPDATE expense_claims
            SET status = :status
            WHERE claim_id = :claim_id
        """), {"status": status_val, "claim_id": claim_id})



def load_manager_team_pending_claims(
    manager_email,
    manager_id,
) -> pd.DataFrame:
    """
    1) Resolve manager's employee_id (from email if needed)
    2) Get all employees where employees.manager_id = <manager_emp_id>
    3) Fetch all expense_claims with employee_id IN (team_ids) and status in ('Pending Review','Pending')
       NOTE: handles TEXT details column by casting to jsonb when extracting vendor.
    Returns a dataframe with claim rows (no LIMIT).
    """

    # 1) Resolve manager_id if not provided
    if not manager_id:
        if not manager_email:
            return _empty_df([
                "claim_id","employee_id","user_name","claim_type",
                "amount","currency","status","vendor_name","claim_date"
            ])
        sql_mgr = """
            SELECT employee_id
            FROM employees
            WHERE LOWER(email) = LOWER(%(email)s)
            LIMIT 1
        """
        mgr_df, err = _safe_read_sql(sql_mgr, {"email": manager_email})
        if err or mgr_df.empty:
            return _empty_df([
                "claim_id","employee_id","user_name","claim_type",
                "amount","currency","status","vendor_name","claim_date"
            ])
        manager_id = mgr_df.iloc[0]["employee_id"]

    # 2) Direct reports under this manager
    sql_team = """
        SELECT employee_id
        FROM employees
        WHERE manager_id = %(mgr_id)s
    """
    team_df, err = _safe_read_sql(sql_team, {"mgr_id": manager_id})
    if err or team_df.empty:
        return _empty_df([
            "claim_id","employee_id","user_name","claim_type",
            "amount","currency","status","vendor_name","claim_date"
        ])

    emp_ids: List[str] = (
        team_df["employee_id"].dropna().astype(str).unique().tolist()
    )
    if not emp_ids:
        return _empty_df([
            "claim_id","employee_id","user_name","claim_type",
            "amount","currency","status","vendor_name","claim_date"
        ])

    # 3) Pending claims for those employee_ids (NO LIMIT)
    # - Cast Python list to text[] with ::text[]
    # - Safely cast details TEXT to jsonb only when non-empty, then ->> 'vendor'
    sql_claims = """
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
            COALESCE(
                ec.vendor_name,
                CASE
                    WHEN ec.details IS NOT NULL AND ec.details <> ''
                    THEN (ec.details::jsonb ->> 'vendor')
                    ELSE NULL
                END
            ) AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        INNER JOIN employees e
            ON e.employee_id = ec.employee_id
        WHERE
            ec.employee_id = ANY(%(emp_ids)s::text[])
            AND ec.status IN ('Pending Review', 'Pending')
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
    """
    df, err = _safe_read_sql(sql_claims, {"emp_ids": emp_ids})
    if err:
        return _empty_df([
            "claim_id","employee_id","user_name","claim_type",
            "amount","currency","status","vendor_name","claim_date"
        ])

    # If claim_date is string, try making it datetime for nicer Streamlit formatting
    if "claim_date" in df.columns:
        try:
            df["claim_date"] = pd.to_datetime(df["claim_date"])
        except Exception:
            pass

    return df



def load_finance_pending_claims() -> pd.DataFrame:
    """
    Return ALL claims that are routed to Finance:
      status = 'Finance Pending'
    Includes vendor_name fallback from details JSON (if text column).
    No LIMIT here (caller/Streamlit can paginate if needed).
    """
    sql_claims = """
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
            COALESCE(
                ec.vendor_name,
                CASE
                    WHEN ec.details IS NOT NULL AND ec.details <> ''
                    THEN (ec.details::jsonb ->> 'vendor')
                    ELSE NULL
                END
            ) AS vendor_name,
            ec.claim_date
        FROM expense_claims ec
        INNER JOIN employees e
            ON e.employee_id = ec.employee_id
        WHERE
            ec.status = 'Finance Pending'
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
    """
    df, err = _safe_read_sql(sql_claims, params=None)
    if err:
        return _empty_df([
            "claim_id","employee_id","user_name","claim_type",
            "amount","currency","status","vendor_name","claim_date"
        ])

    if "claim_date" in df.columns:
        try:
            df["claim_date"] = pd.to_datetime(df["claim_date"])
        except Exception:
            pass

    return df


def finance_update_claim_decision(claim_id: str, decision: str, comment: str, approver_id: str) -> None:
    """
    decision: 'Approve' or 'Reject'
    Updates expense_claims.status, and (optionally) finance_comment/finance_approver_id if your schema supports them.
    """
    status_val = "Approved" if decision == "Approve" else "Rejected"
    with engine.begin() as conn:
        # If your table has these columns, use this block:
        # conn.execute(text("""
        #     UPDATE expense_claims
        #     SET status = :status,
        #         finance_comment = :comment,
        #         finance_approver_id = :fid
        #     WHERE claim_id = :cid
        # """), {"status": status_val, "comment": comment, "fid": approver_id, "cid": claim_id})

        # Minimal update (status only)
        conn.execute(text("""
            UPDATE expense_claims
            SET status = :status
            WHERE claim_id = :cid
        """), {"status": status_val, "cid": claim_id})