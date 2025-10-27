

import os
import json
import datetime as dt
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import sqlalchemy as _sql
from sqlalchemy import text

import database as _database  # expects DATABASE_URL in database.py

# ------------------------------------------------------------------
# 1. ENGINE SETUP
# ------------------------------------------------------------------
DATABASE_URL = _database.DATABASE_URL
engine = _sql.create_engine(DATABASE_URL, future=True)


# ------------------------------------------------------------------
# 2. LOW-LEVEL HELPERS
# ------------------------------------------------------------------

def _empty_df(columns=None):
    return pd.DataFrame(columns=columns or [])

def _safe_read_sql(sql: str, params: dict | None = None) -> Tuple[pd.DataFrame, Optional[Exception]]:
    """
    Run a SELECT safely. Returns (df, err). On error returns (empty_df, ex).
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params or {})
        return df, None
    except Exception as ex:
        print(f"[db_utils] SQL error: {ex}")
        return _empty_df(), ex

def _fetch_scalar(sql: str, params: dict | None = None):
    """
    Run a scalar query like COUNT(*), SUM(...).
    Returns python value or None.
    """
    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql), params or {}).scalar()
        return row
    except Exception as ex:
        print(f"[db_utils] _fetch_scalar error: {ex}")
        return None

def get_engine():
    """
    Unified engine accessor for Streamlit / FastAPI.
    """
    return engine


# ------------------------------------------------------------------
# 3. CORE DATA OPS (from existing db_utils.py)
# ------------------------------------------------------------------

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
    # emp_id currently unused in your SQL, kept to preserve signature
    sql = "SELECT * FROM per_diem_rates;"
    df, err = _safe_read_sql(sql)
    if err:
        return []
    return df.to_dict(orient="records")

def generate_claim_id():
    """
    CLM-YYYYMMDD-XXXX (XXXX = count+1 snapshot at call time)
    """
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
    Insert one row into expense_claims using normalized payload.
    status can be:
      - plain string ("Auto Approved", "Pending Review", ...)
      - validator result dict
    """
    now = datetime.now()
    claim_id = f"CLM-{now.strftime('%Y%m%d-%H%M%S')}"

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
        status_val = status

    linked_booking_id = None

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
        "payment_mode": payment_mode,
        "status_from_tag": status_val,
        "auto_approved_from_tag": auto_approved_flag,
        "raw_tag": "",
    }

    def _to_json_truncated(obj, max_len: int):
        s = json.dumps(obj, ensure_ascii=False, default=str)
        return s if len(s) <= max_len else (s[: max_len - 3] + "...")

    DETAILS_MAX = 4000
    OTHERS1_MAX = 4000

    Details = _to_json_truncated(details_obj, DETAILS_MAX)
    Others_1 = _to_json_truncated(payload_out, OTHERS1_MAX)
    Others_2 = None

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
                "auto_approved": bool(auto_approved_flag),
                "is_duplicate": False,
                "fraud_flag": False,
            },
        )

    return claim_id

def log_validation_result(claim_id: str, employee_id: str, validation_obj: dict):
    """
    Write a snapshot of validator output into expense_validation_logs.
    """
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

def manager_update_claim_decision(claim_id: str, decision: str, comment: str, approver_id: str) -> None:
    """
    Manager action on claim.
    decision: 'Approve' or 'Reject'
    """
    status_val = "Approved" if decision == "Approve" else "Rejected"
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE expense_claims
            SET status = :status
            WHERE claim_id = :claim_id
        """), {"status": status_val, "claim_id": claim_id})

def finance_update_claim_decision(claim_id: str, decision: str, comment: str, approver_id: str) -> None:
    """
    Finance action on claim.
    decision: 'Approve' or 'Reject'
    """
    status_val = "Approved" if decision == "Approve" else "Rejected"
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE expense_claims
            SET status = :cid_status
            WHERE claim_id = :cid
        """), {"cid_status": status_val, "cid": claim_id})


# ------------------------------------------------------------------
# 4. DASHBOARD / WORKFLOW QUERIES
# ------------------------------------------------------------------

def load_recent_claims(emp_id: str, limit: int = 50) -> pd.DataFrame:
    """
    Employee self-view of their own recent claims.
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
        return _empty_df([
            "claim_id","employee_id","user_name","claim_type",
            "amount","currency","status","vendor_name","claim_date"
        ])
    return df

def load_manager_team_pending_claims(manager_email: Optional[str], manager_id: Optional[str]) -> pd.DataFrame:
    """
    1) Resolve manager_id from email if needed
    2) Get direct reports
    3) Fetch Pending/Pending Review claims for those reports
    """
    # Step 1: get manager_id if missing
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

    # Step 2: team members
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

    # Step 3: pending claims for those employees
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
            ec.employee_id = ANY(:emp_ids)
            AND ec.status IN ('Pending Review','Pending')
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
    """
    # SQLAlchemy can't bind python list directly into ANY(:emp_ids::text[])
    # We'll do manual param expansion:
    with engine.connect() as conn:
        df = pd.read_sql_query(
            text(sql_claims.replace("ANY(:emp_ids)", f"ANY(ARRAY{emp_ids}::text[])")),
            conn
        )

    # try to normalize claim_date
    if "claim_date" in df.columns:
        try:
            df["claim_date"] = pd.to_datetime(df["claim_date"])
        except Exception:
            pass

    return df

def load_finance_pending_claims() -> pd.DataFrame:
    """
    All claims with status 'Finance Pending'
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

def fetch_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Used by portal_login.
    """
    q = text("""
        SELECT 
            email,
            access_label
        FROM employees
        WHERE LOWER(email) = LOWER(:email)
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(q, {"email": email.strip()}).mappings().first()
        return dict(row) if row else None

def load_employee_by_email(email: str) -> Optional[Dict[str, Any]]:
    q = text("SELECT * FROM employees WHERE email = :email;")
    with engine.connect() as conn:
        row = conn.execute(q, {"email": email}).mappings().first()
        return dict(row) if row else None

def load_policies_df(grade: str) -> pd.DataFrame:
    q = text("""
        SELECT *
        FROM expense_policies
        WHERE applicable_grades ILIKE :pattern
        ORDER BY category ASC, max_allowance DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(q, conn, params={"pattern": f"%{grade}%"})


# ------------------------------------------------------------------
# 5. KPI / ANALYTICS QUERIES  (migrated from queries.py)
# ------------------------------------------------------------------
# Helper: build WHERE for date filters, same logic as _date_filter_sql

def _date_filter_sql(start_date: Optional[str], end_date: Optional[str]) -> Tuple[str, dict]:
    """
    Returns (where_sql, params_dict) for claim_date filter.
    """
    wh = []
    params: dict = {}
    if start_date:
        wh.append("claim_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        wh.append("claim_date <= :end_date")
        params["end_date"] = end_date
    where_sql = ("WHERE " + " AND ".join(wh)) if wh else ""
    return where_sql, params

def get_all_claims() -> List[Dict[str, Any]]:
    sql = """
        SELECT *
        FROM expense_claims
        ORDER BY claim_date DESC, claim_id DESC
    """
    with engine.connect() as conn:
        rows = pd.read_sql_query(sql, conn).to_dict(orient="records")
    for r in rows:
        if "amount" in r and r["amount"] is not None:
            r["amount"] = float(r["amount"])
    return rows

def get_total_claims() -> Dict[str, int]:
    val = _fetch_scalar("SELECT COUNT(*) FROM expense_claims")
    return {"total_claims": int(val or 0)}

def get_total_amount() -> Dict[str, float]:
    val = _fetch_scalar("SELECT COALESCE(SUM(amount)::float,0) FROM expense_claims")
    return {"total_amount": float(val or 0.0)}

def get_fraud_stats() -> Dict[str, float | int]:
    frauds = _fetch_scalar("SELECT COUNT(*) FROM expense_claims WHERE fraud_flag = TRUE")
    total = _fetch_scalar("SELECT COUNT(*) FROM expense_claims")
    frauds = int(frauds or 0)
    total = int(total or 0)
    percent = (frauds / total * 100.0) if total else 0.0
    return {"fraud_count": frauds, "fraud_percent": round(percent, 2)}

def get_auto_approved_count() -> Dict[str, int]:
    val = _fetch_scalar("SELECT COUNT(*) FROM expense_claims WHERE auto_approved = TRUE")
    return {"auto_approved": int(val or 0)}

def get_auto_approved_rate() -> Dict[str, float]:
    auto = _fetch_scalar("SELECT COUNT(*) FROM expense_claims WHERE auto_approved = TRUE")
    total = _fetch_scalar("SELECT COUNT(*) FROM expense_claims")
    auto = int(auto or 0)
    total = int(total or 0)
    rate = (auto / total * 100.0) if total else 0.0
    return {"auto_approved_rate": round(rate, 2)}

def get_avg_amount_per_employee(limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT employee_id,
               ROUND(AVG(amount)::numeric, 2)::float AS avg_amount
        FROM expense_claims
        GROUP BY employee_id
        ORDER BY avg_amount DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"lim": limit}).to_dict(orient="records")
    for r in rows:
        if r.get("avg_amount") is not None:
            r["avg_amount"] = float(r["avg_amount"])
    return {"avg_claim_amounts": rows}

def get_top_vendors(limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT
            COALESCE(vendor_name, 'Unknown') AS vendor_name,
            SUM(amount)::float AS total_spent
        FROM expense_claims
        GROUP BY COALESCE(vendor_name, 'Unknown')
        ORDER BY total_spent DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"lim": limit}).to_dict(orient="records")
    for r in rows:
        if r.get("total_spent") is not None:
            r["total_spent"] = float(r["total_spent"])
    return {"top_vendors": rows}

def get_claims_by_category() -> Dict[str, List[Dict[str, Any]]]:
    sql = """
        SELECT
            COALESCE(expense_category, 'unknown') AS expense_category,
            COUNT(*) AS total_claims,
            COALESCE(SUM(amount)::float, 0) AS total_amount
        FROM expense_claims
        GROUP BY COALESCE(expense_category, 'unknown')
        ORDER BY total_amount DESC
    """
    with engine.connect() as conn:
        rows = pd.read_sql_query(sql, conn).to_dict(orient="records")
    for r in rows:
        r["total_claims"] = int(r.get("total_claims", 0) or 0)
        r["total_amount"] = float(r.get("total_amount", 0.0) or 0.0)
    return {"claims_by_category": rows}

def get_table_health() -> Dict[str, bool]:
    tables = [
        "expense_claims",
        "employees",
        "expense_policies",
        "expense_validation_logs",
        "per_diem_rates",
        "vendors",
    ]
    checks: Dict[str, bool] = {}
    with engine.connect() as conn:
        for t in tables:
            # to_regclass() returns NULL if table doesn't exist
            row = conn.execute(
                text("SELECT to_regclass(:tname) IS NOT NULL AS exists"),
                {"tname": t},
            ).mappings().first()
            checks[t] = bool(row["exists"]) if row else False
    return checks

def get_claims_by_date(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    where_sql, params = _date_filter_sql(start_date, end_date)
    sql = f"""
        SELECT
            claim_date::date AS dt,
            COUNT(*) AS total_claims,
            COALESCE(SUM(amount)::float, 0) AS total_amount
        FROM expense_claims
        {where_sql}
        GROUP BY dt
        ORDER BY dt
    """
    with engine.connect() as conn:
        rows = pd.read_sql_query(text(sql), conn, params=params).to_dict(orient="records")
    for r in rows:
        r["total_claims"] = int(r["total_claims"] or 0)
        r["total_amount"] = float(r["total_amount"] or 0.0)
    return {"by_date": rows}

def get_automation_rate_by_date(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    where_sql, params = _date_filter_sql(start_date, end_date)
    sql = f"""
        SELECT
            claim_date::date AS dt,
            SUM(CASE WHEN auto_approved = TRUE THEN 1 ELSE 0 END) AS auto_approved,
            COUNT(*) AS total
        FROM expense_claims
        {where_sql}
        GROUP BY dt
        ORDER BY dt
    """
    with engine.connect() as conn:
        rows = pd.read_sql_query(text(sql), conn, params=params).to_dict(orient="records")
    for r in rows:
        auto = int(r["auto_approved"] or 0)
        total = int(r["total"] or 0)
        r["automation_rate"] = round((auto / total) if total else 0.0, 4)
    return {"by_date": rows}

def get_processing_time_by_date(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    """
    Placeholder: no approved_at/finalized_at columns in schema yet.
    """
    return {
        "by_date": [],
        "note": "Processing-time columns not detected; implement when approved_at/finalized_at exist."
    }

def get_avg_processing_time_by_date() -> Dict[str, Any]:
    """
    Placeholder for high-level avg processing time.
    """
    return {"avg_processing_time_days": None}

def get_claims_by_department(limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT
            COALESCE(e.department, 'Unknown') AS department,
            COUNT(*) AS total_claims,
            COALESCE(SUM(c.amount)::float, 0) AS total_amount
        FROM expense_claims c
        LEFT JOIN employees e ON e.employee_id = c.employee_id
        GROUP BY COALESCE(e.department, 'Unknown')
        ORDER BY total_amount DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"lim": limit}).to_dict(orient="records")
    for r in rows:
        r["total_claims"] = int(r["total_claims"] or 0)
        r["total_amount"] = float(r["total_amount"] or 0.0)
    return {"by_department": rows}

def get_top_employees(limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT
            c.employee_id,
            TRIM(COALESCE(e.first_name, '') || ' ' || COALESCE(e.last_name, '')) AS employee_name,
            COUNT(*) AS total_claims,
            COALESCE(SUM(c.amount)::float, 0) AS total_amount
        FROM expense_claims c
        LEFT JOIN employees e ON e.employee_id = c.employee_id
        GROUP BY c.employee_id,
                 TRIM(COALESCE(e.first_name, '') || ' ' || COALESCE(e.last_name, ''))
        ORDER BY total_amount DESC
        LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"lim": limit}).to_dict(orient="records")
    for r in rows:
        r["total_claims"] = int(r["total_claims"] or 0)
        r["total_amount"] = float(r["total_amount"] or 0.0)
    return {"top_employees": rows}

def get_fraud_flags(limit: int = 50, offset: int = 0) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT
            claim_id,
            employee_id,
            expense_category,
            amount::float AS amount,
            currency,
            vendor_name,
            status,
            claim_date,
            auto_approved,
            fraud_flag
        FROM expense_claims
        WHERE fraud_flag = TRUE
        ORDER BY claim_date DESC, claim_id DESC
        OFFSET :off LIMIT :lim
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"off": offset, "lim": limit}).to_dict(orient="records")
    for r in rows:
        if r.get("amount") is not None:
            r["amount"] = float(r["amount"])
    return {"fraud_flags": rows}

def get_duplicates(threshold: int = 2) -> Dict[str, List[Dict[str, Any]]]:
    sql = text("""
        SELECT
            employee_id,
            currency,
            COALESCE(vendor_name, 'Unknown') AS vendor_name,
            claim_date::date AS dt,
            amount::float AS amount,
            COUNT(*) AS occurrences,
            ARRAY_AGG(claim_id ORDER BY claim_id) AS claim_ids
        FROM expense_claims
        GROUP BY employee_id, currency,
                 COALESCE(vendor_name, 'Unknown'),
                 claim_date::date,
                 amount
        HAVING COUNT(*) >= :th
        ORDER BY occurrences DESC, dt DESC
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(sql, conn, params={"th": threshold}).to_dict(orient="records")
    for r in rows:
        r["amount"] = float(r["amount"] or 0.0)
        r["occurrences"] = int(r["occurrences"] or 0)
    return {"duplicates": rows}

def get_amount_distribution(buckets: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create histogram buckets across 'amount'.
    """
    if not buckets or len(buckets) < 2:
        return {"buckets": [], "counts": []}

    # Build CASE SUMs dynamically
    ranges = []
    params: dict = {}
    sum_cases_sql_parts = []

    for i in range(len(buckets) - 1):
        a = buckets[i]
        b = buckets[i + 1]
        label = f"{a}-{b}"
        ranges.append(label)
        sum_cases_sql_parts.append(
            f"SUM(CASE WHEN amount >= {a} AND amount < {b} THEN 1 ELSE 0 END) AS b{i}"
        )

    last_label = f"{buckets[-1]}+"
    sum_cases_sql_parts.append(
        f"SUM(CASE WHEN amount >= {buckets[-1]} THEN 1 ELSE 0 END) AS b_last"
    )

    sql = f"SELECT {', '.join(sum_cases_sql_parts)} FROM expense_claims"

    with engine.connect() as conn:
        row = pd.read_sql_query(sql, conn, params=params)
    if row.empty:
        return {"buckets": [], "counts": []}

    counts: List[int] = []
    for i in range(len(buckets) - 1):
        counts.append(int(row.iloc[0][f"b{i}"] or 0))
    counts.append(int(row.iloc[0]["b_last"] or 0))

    labels = ranges + [last_label]
    return {"buckets": labels, "counts": counts}

def get_pending_aging() -> Dict[str, List[Dict[str, Any]]]:
    pending_statuses = ("Pending", "Pending Review", "Manager Pending", "Finance Pending")
    sql = text("""
        SELECT
            claim_id,
            employee_id,
            expense_category,
            amount::float AS amount,
            currency,
            vendor_name,
            status,
            claim_date::date AS claim_date,
            GREATEST(0, (CURRENT_DATE - claim_date::date))::int AS age_days
        FROM expense_claims
        WHERE status = ANY(:pending_list)
        ORDER BY age_days DESC, claim_date ASC
        LIMIT 500
    """)
    with engine.connect() as conn:
        rows = pd.read_sql(
            sql,
            conn,
            params={"pending_list": list(pending_statuses)}
        ).to_dict(orient="records")

    for r in rows:
        if r.get("amount") is not None:
            r["amount"] = float(r["amount"])
        r["age_days"] = int(r.get("age_days", 0) or 0)
    return {"pending": rows}

def get_claim_details(claim_id: str) -> Dict[str, Any] | None:
    sql = text("""
        SELECT
            c.*,
            e.first_name,
            e.last_name,
            e.email,
            e.department,
            e.cost_center,
            e.grade
        FROM expense_claims c
        LEFT JOIN employees e ON e.employee_id = c.employee_id
        WHERE c.claim_id = :cid
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"cid": claim_id}).mappings().first()
        if not row:
            return None
        row = dict(row)
    if "amount" in row and row["amount"] is not None:
        row["amount"] = float(row["amount"])
    return row


# ------------------------------------------------------------------
# 6. HIGH-LEVEL ROLLUP
# ------------------------------------------------------------------

def get_claims_summary() -> Dict[str, Any]:
    """
    Consolidated KPI summary (was queries.get_claims_summary()).
    """
    out: Dict[str, Any] = {}
    out.update(get_total_claims())
    out.update(get_total_amount())
    out.update(get_fraud_stats())
    out.update(get_auto_approved_count())
    out.update(get_auto_approved_rate())
    out.update(get_claims_by_category())
    out.update(get_top_vendors(limit=10))
    out.update(get_avg_amount_per_employee(limit=10))
    return out


# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# db_utils.py
import json
import datetime as dt
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import sqlalchemy as _sql
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String

import database as _database  # single source of truth

engine = _database.get_engine()

# ---------- helpers ----------
def _empty_df(columns=None):
    return pd.DataFrame(columns=columns or [])

def _safe_read_sql(sql: str, params: dict | None = None) -> tuple[pd.DataFrame, Optional[Exception]]:
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn, params=params or {})
        return df, None
    except Exception as ex:
        print(f"[db_utils] SQL error: {ex}")
        return _empty_df(), ex

def _fetch_scalar(sql: str, params: dict | None = None):
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar()
    except Exception as ex:
        print(f"[db_utils] _fetch_scalar error: {ex}")
        return None

# ---------- core lookups ----------
def get_employee_details(emp_id: str):
    sql = """
        SELECT *
        FROM employees
        WHERE employee_id = %(emp_id)s
        LIMIT 1
    """
    df, err = _safe_read_sql(sql, {"emp_id": emp_id})
    return [] if err else df.to_dict(orient="records")

def get_expense_policy():
    df, err = _safe_read_sql("SELECT * FROM expense_policies;")
    return [] if err else df.to_dict(orient="records")

def get_per_diem_rates(emp_id: str | None = None):
    df, err = _safe_read_sql("SELECT * FROM per_diem_rates;")
    return [] if err else df.to_dict(orient="records")

def generate_claim_id():
    date_prefix = dt.datetime.now().strftime("%Y%m%d")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM expense_claims")).scalar() or 0
            nxt = int(result) + 1
    except Exception as ex:
        print(f"[db_utils] generate_claim_id error: {ex}")
        nxt = 1
    return f"CLM-{date_prefix}-{nxt:04d}"

def save_expense_claim(payload_out: dict, status) -> str:
    now = datetime.now()
    claim_id = f"CLM-{now.strftime('%Y%m%d-%H%M%S')}"

    employee_id = payload_out.get("employee_id")
    expense_category = payload_out.get("category", "other")
    amount = float(payload_out.get("total_amount", 0.0) or 0.0)
    currency = payload_out.get("currency", "INR")
    vendor_name = (payload_out.get("vendor") or "").strip() or None
    receipt_id = payload_out.get("invoice_id") or payload_out.get("invoice_number") or None

    claim_date = payload_out.get("expense_date")
    db_claim_date = claim_date if isinstance(claim_date, str) and claim_date else now.strftime("%Y-%m-%d")

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
        status_val = status

    details_obj = {
        "invoice_id": payload_out.get("invoice_id"),
        "employee_id": employee_id,
        "expense_date": payload_out.get("expense_date"),
        "vendor": payload_out.get("vendor"),
        "total_amount": amount,
        "currency": currency,
        "category": expense_category,
        "travel_block": payload_out.get("travel_block"),
        "booking_details": payload_out.get("booking_details"),
        "food_details": payload_out.get("food_details"),
        "other_details": payload_out.get("other_details"),
        "payment_mode": payment_mode,
        "status_from_tag": status_val,
        "auto_approved_from_tag": auto_approved_flag,
        "raw_tag": "",
    }

    def _trunc(obj, max_len: int):
        s = json.dumps(obj, ensure_ascii=False, default=str)
        return s if len(s) <= max_len else (s[: max_len - 3] + "...")

    insert_sql = text("""
        INSERT INTO expense_claims (
            claim_id, employee_id, claim_date, expense_category, amount, currency,
            vendor_name, linked_booking_id, receipt_id, payment_mode, status,
            Details, Others_1, Others_2, auto_approved, is_duplicate, fraud_flag
        ) VALUES (
            :claim_id, :employee_id, :claim_date, :expense_category, :amount, :currency,
            :vendor_name, :linked_booking_id, :receipt_id, :payment_mode, :status,
            :Details, :Others_1, :Others_2, :auto_approved, :is_duplicate, :fraud_flag
        )
    """)

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
                "linked_booking_id": None,
                "receipt_id": receipt_id,
                "payment_mode": payment_mode,
                "status": status_val,
                "Details": _trunc(details_obj, 4000),
                "Others_1": _trunc(payload_out, 4000),
                "Others_2": None,
                "auto_approved": bool(auto_approved_flag),
                "is_duplicate": False,
                "fraud_flag": False,
            },
        )
    return claim_id

def log_validation_result(claim_id: str, employee_id: str, validation_obj: dict):
    # expects a dict; caller must NOT pass a string
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
            claim_id, employee_id, status_val, payment_mode, auto_approved, raw_validation_json
        ) VALUES (
            :claim_id, :employee_id, :status_val, :payment_mode, :auto_approved, :raw
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
                "raw": json.dumps(validation_obj, default=str),
            },
        )
    return {
        "claim_id": claim_id,
        "status_val": status_val,
        "payment_mode": payment_mode,
        "auto_approved": auto_approved,
    }

def update_claim_status(claim_id: str, status_val: str, auto_approved: bool):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE expense_claims
                SET status = :status_val, auto_approved = :auto_approved
                WHERE claim_id = :claim_id
            """),
            {"claim_id": claim_id, "status_val": status_val, "auto_approved": auto_approved},
        )

# ---------- dashboard/workflow ----------
def load_recent_claims(emp_id: str, limit: int = 50) -> pd.DataFrame:
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), ec.employee_id) AS user_name,
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
        LEFT JOIN employees e ON e.employee_id = ec.employee_id
        WHERE ec.employee_id = %(emp_id)s
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
        LIMIT %(limit)s
    """
    df, err = _safe_read_sql(sql, {"emp_id": emp_id, "limit": int(limit)})
    if err:
        return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])
    return df

def load_manager_team_pending_claims(manager_email: Optional[str], manager_id: Optional[str]) -> pd.DataFrame:
    if not manager_id:
        if not manager_email:
            return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])
        mgr_sql = "SELECT employee_id FROM employees WHERE LOWER(email)=LOWER(%(email)s) LIMIT 1"
        mgr_df, err = _safe_read_sql(mgr_sql, {"email": manager_email})
        if err or mgr_df.empty:
            return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])
        manager_id = mgr_df.iloc[0]["employee_id"]

    team_sql = "SELECT employee_id FROM employees WHERE manager_id = %(mgr_id)s"
    team_df, err = _safe_read_sql(team_sql, {"mgr_id": manager_id})
    if err or team_df.empty:
        return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])

    emp_ids = team_df["employee_id"].dropna().astype(str).unique().tolist()
    if not emp_ids:
        return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])

    sql = text("""
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), ec.employee_id) AS user_name,
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
        INNER JOIN employees e ON e.employee_id = ec.employee_id
        WHERE ec.employee_id = ANY(:emp_ids)
          AND ec.status IN ('Pending Review','Pending')
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
    """).bindparams(_sql.bindparam("emp_ids", type_=ARRAY(String())))
    with engine.connect() as conn:
        return pd.read_sql_query(sql, conn, params={"emp_ids": emp_ids})

def load_finance_pending_claims() -> pd.DataFrame:
    sql = """
        SELECT
            ec.claim_id,
            ec.employee_id,
            COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), ec.employee_id) AS user_name,
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
        INNER JOIN employees e ON e.employee_id = ec.employee_id
        WHERE ec.status = 'Finance Pending'
        ORDER BY ec.claim_date DESC, ec.claim_id DESC
    """
    df, err = _safe_read_sql(sql)
    if err:
        return _empty_df(["claim_id","employee_id","user_name","claim_type","amount","currency","status","vendor_name","claim_date"])
    try:
        if "claim_date" in df.columns:
            df["claim_date"] = pd.to_datetime(df["claim_date"])
    except Exception:
        pass
    return df

# ---------- policy & misc ----------
def fetch_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    q = text("""
        SELECT email, access_label
        FROM employees
        WHERE LOWER(email) = LOWER(:email)
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(q, {"email": email.strip()}).mappings().first()
        return dict(row) if row else None

def load_employee_by_email(email: str) -> Optional[Dict[str, Any]]:
    q = text("SELECT * FROM employees WHERE email = :email;")
    with engine.connect() as conn:
        row = conn.execute(q, {"email": email}).mappings().first()
        return dict(row) if row else None

def load_policies_df(grade: str) -> pd.DataFrame:
    q = text("""
        SELECT *
        FROM expense_policies
        WHERE applicable_grades ILIKE :pattern
        ORDER BY category ASC, max_allowance DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(q, conn, params={"pattern": f"%{grade}%"})
