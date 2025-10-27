# queries.py

from typing import Dict, List, Any, Optional, Tuple
import re
from db import get_connection, safe_query, close_connection_pool

def _fetchval(conn, sql: str, params: tuple | list | None = None, key: str = "val"):
    """
    Execute a SELECT returning a single scalar value.
    Accepts either:
      - an expression with no FROM (e.g., "NOW()", "42")
      - an expression followed by FROM ... (e.g., "COUNT(*) FROM table", "COALESCE(SUM(x),0) FROM t")
    We generate a valid SELECT that aliases the expression as `key`.
    """
    # Find case-insensitive ' from ' boundary (with surrounding spaces to avoid column names)
    m = re.search(r"\sfrom\s", sql, flags=re.IGNORECASE)
    if m:
        # expression BEFORE FROM, and the rest starting at FROM
        expr = sql[:m.start()].strip()
        rest = sql[m.start():]  # includes the 'FROM ...'
        query = f"SELECT {expr} AS {key} {rest}"
    else:
        # no FROM clause: wrap as scalar expression
        query = f"SELECT ({sql}) AS {key}"

    rows = safe_query(conn, query, params)
    if rows and key in rows[0]:
        return rows[0][key]
    return None


def _date_filter_sql(start_date: Optional[str], end_date: Optional[str]) -> Tuple[str, list]:
    """
    Build WHERE fragments for optional start_date/end_date on claim_date.
    Returns (sql_fragment, params_list).
    """
    wh = []
    params: list = []
    if start_date:
        wh.append("claim_date >= %s")
        params.append(start_date)
    if end_date:
        wh.append("claim_date <= %s")
        params.append(end_date)
    where_sql = ("WHERE " + " AND ".join(wh)) if wh else ""
    return where_sql, params


# ------------------------------------------------------------------
# Existing queries (kept)
# ------------------------------------------------------------------

def get_all_claims() -> List[Dict[str, Any]]:
    """
    Fetch all claims ordered by claim_date (DESC).
    """
    with get_connection() as conn:
        rows = safe_query(
            conn,
            "SELECT * FROM expense_claims ORDER BY claim_date DESC, claim_id DESC"
        )
        for r in rows:
            if "amount" in r and r["amount"] is not None:
                r["amount"] = float(r["amount"])
        return rows


def get_total_claims() -> Dict[str, int]:
    with get_connection() as conn:
        val = _fetchval(conn, "COUNT(*) FROM expense_claims", key="total_claims")
        return {"total_claims": int(val or 0)}


def get_total_amount() -> Dict[str, float]:
    with get_connection() as conn:
        val = _fetchval(conn, "COALESCE(SUM(amount)::float, 0) FROM expense_claims", key="total_amount")
        return {"total_amount": float(val or 0.0)}


def get_fraud_stats() -> Dict[str, float | int]:
    with get_connection() as conn:
        frauds = _fetchval(conn, "COUNT(*) FROM expense_claims WHERE fraud_flag = TRUE", key="c")
        total = _fetchval(conn, "COUNT(*) FROM expense_claims", key="t")
        frauds = int(frauds or 0)
        total = int(total or 0)
        percent = (frauds / total * 100.0) if total else 0.0
        return {"fraud_count": frauds, "fraud_percent": round(percent, 2)}


def get_auto_approved_rate() -> Dict[str, float]:
    with get_connection() as conn:
        auto = _fetchval(conn, "COUNT(*) FROM expense_claims WHERE auto_approved = TRUE", key="a")
        total = _fetchval(conn, "COUNT(*) FROM expense_claims", key="t")
        auto = int(auto or 0)
        total = int(total or 0)
        rate = (auto / total * 100.0) if total else 0.0
        return {"auto_approved_rate": round(rate, 2)}


def get_avg_amount_per_employee(limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT employee_id, ROUND(AVG(amount)::numeric, 2)::float AS avg_amount
            FROM expense_claims
            GROUP BY employee_id
            ORDER BY avg_amount DESC
            LIMIT %s
        """, (limit,))
        for r in rows:
            if "avg_amount" in r and r["avg_amount"] is not None:
                r["avg_amount"] = float(r["avg_amount"])
        return {"avg_claim_amounts": rows}


def get_top_vendors(limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT
                COALESCE(vendor_name, 'Unknown') AS vendor_name,
                SUM(amount)::float AS total_spent
            FROM expense_claims
            GROUP BY COALESCE(vendor_name, 'Unknown')
            ORDER BY total_spent DESC
            LIMIT %s
        """, (limit,))
        for r in rows:
            if "total_spent" in r and r["total_spent"] is not None:
                r["total_spent"] = float(r["total_spent"])
        return {"top_vendors": rows}


def get_claims_by_category() -> Dict[str, List[Dict[str, Any]]]:
    with get_connection() as conn:
        rows = safe_query(conn, """
            SELECT
                COALESCE(expense_category, 'unknown') AS expense_category,
                COUNT(*) AS total_claims,
                COALESCE(SUM(amount)::float, 0) AS total_amount
            FROM expense_claims
            GROUP BY COALESCE(expense_category, 'unknown')
            ORDER BY total_amount DESC
        """)
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
    with get_connection() as conn:
        for t in tables:
            rows = safe_query(conn, "SELECT to_regclass(%s) IS NOT NULL AS exists;", (t,))
            checks[t] = bool(rows[0]["exists"]) if rows else False
    return checks


# ------------------------------------------------------------------
# New queries to back your routes (no new input params added)
# ------------------------------------------------------------------

def get_claims_summary() -> Dict[str, Any]:
    """
    Consolidated KPI summary for /claims/summary.
    Gracefully handles missing tables or partial failures.
    """
    out: Dict[str, Any] = {}

    # Safe execution wrapper
    def safe_call(func, default: Dict[str, Any]):
        try:
            return func()
        except Exception as e:
            print(f"[WARN] {func.__name__} failed: {e}")
            return default

    # Collect metrics safely
    out.update(safe_call(get_total_claims, {"total_claims": 0}))
    out.update(safe_call(get_total_amount, {"total_amount": 0.0}))
    out.update(safe_call(get_fraud_stats, {"fraud_count": 0, "fraud_percent": 0.0}))
    out.update(safe_call(get_auto_approved_count, {"auto_approved": 0}))
    out.update(safe_call(get_auto_approved_rate, {"auto_approved_rate": 0.0}))
    out.update(safe_call(get_claims_by_category, {"claims_by_category": []}))
    out.update(safe_call(lambda: get_top_vendors(limit=10), {"top_vendors": []}))
    out.update(safe_call(lambda: get_avg_amount_per_employee(limit=10), {"avg_claim_amounts": []}))

    return out



def get_auto_approved_count() -> Dict[str, int]:
    with get_connection() as conn:
        val = _fetchval(conn, "COUNT(*) FROM expense_claims WHERE auto_approved = TRUE", key="auto_approved")
        return {"auto_approved": int(val or 0)}


def get_claims_by_date(start_date: str | None, end_date: str | None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns daily totals within an optional date range.
    """
    where_sql, params = _date_filter_sql(start_date, end_date)
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT
                claim_date::date AS dt,
                COUNT(*) AS total_claims,
                COALESCE(SUM(amount)::float, 0) AS total_amount
            FROM expense_claims
            {where_sql}
            GROUP BY dt
            ORDER BY dt
        """, params)
        for r in rows:
            r["total_claims"] = int(r["total_claims"] or 0)
            r["total_amount"] = float(r["total_amount"] or 0.0)
        return {"by_date": rows}


def get_automation_rate_by_date(start_date: str | None, end_date: str | None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Daily automation: auto_approved / total
    """
    where_sql, params = _date_filter_sql(start_date, end_date)
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT
                claim_date::date AS dt,
                SUM(CASE WHEN auto_approved = TRUE THEN 1 ELSE 0 END) AS auto_approved,
                COUNT(*) AS total
            FROM expense_claims
            {where_sql}
            GROUP BY dt
            ORDER BY dt
        """, params)
        for r in rows:
            auto = int(r["auto_approved"] or 0)
            total = int(r["total"] or 0)
            r["automation_rate"] = round((auto/total) if total else 0.0, 4)
        return {"by_date": rows}


def get_processing_time_by_date(start_date: str | None, end_date: str | None) -> Dict[str, Any]:
    """
    SAFE default implementation without assuming non-existent columns.
    If your schema has `approved_at` / `finalized_at`, replace this with an AVG over (approved_at - claim_date).
    Returns an empty series plus a note (so routes don't break).
    """
    return {"by_date": [], "note": "Processing-time columns not detected; implement when approved_at/finalized_at exist."}


def get_avg_processing_time_by_date() -> Dict[str, Any]:
    """
    Used by /claims/summary to merge in processing time info without breaking if fields are missing.
    """
    return {"avg_processing_time_days": None}


def get_claims_by_department(limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT
                COALESCE(e.department, 'Unknown') AS department,
                COUNT(*) AS total_claims,
                COALESCE(SUM(c.amount)::float, 0) AS total_amount
            FROM expense_claims c
            LEFT JOIN employees e ON e.employee_id = c.employee_id
            GROUP BY COALESCE(e.department, 'Unknown')
            ORDER BY total_amount DESC
            LIMIT %s
        """, (limit,))
        for r in rows:
            r["total_claims"] = int(r["total_claims"] or 0)
            r["total_amount"] = float(r["total_amount"] or 0.0)
        return {"by_department": rows}


def get_top_employees(limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
    """
    Top employees by total amount.
    """
    with get_connection() as conn:
        rows = safe_query(conn, f"""
            SELECT
                c.employee_id,
                TRIM(COALESCE(e.first_name, '') || ' ' || COALESCE(e.last_name, '')) AS employee_name,
                COUNT(*) AS total_claims,
                COALESCE(SUM(c.amount)::float, 0) AS total_amount
            FROM expense_claims c
            LEFT JOIN employees e ON e.employee_id = c.employee_id
            GROUP BY c.employee_id, TRIM(COALESCE(e.first_name, '') || ' ' || COALESCE(e.last_name, ''))
            ORDER BY total_amount DESC
            LIMIT %s
        """, (limit,))
        for r in rows:
            r["total_claims"] = int(r["total_claims"] or 0)
            r["total_amount"] = float(r["total_amount"] or 0.0)
        return {"top_employees": rows}


def get_fraud_flags(limit: int = 50, offset: int = 0) -> Dict[str, List[Dict[str, Any]]]:
    with get_connection() as conn:
        rows = safe_query(conn, """
            SELECT
                claim_id, employee_id, expense_category, amount::float AS amount,
                currency, vendor_name, status, claim_date, auto_approved, fraud_flag
            FROM expense_claims
            WHERE fraud_flag = TRUE
            ORDER BY claim_date DESC, claim_id DESC
            OFFSET %s LIMIT %s
        """, (offset, limit))
        for r in rows:
            if r.get("amount") is not None:
                r["amount"] = float(r["amount"])
        return {"fraud_flags": rows}


def get_duplicates(threshold: int = 2) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identify potential duplicate claims by (employee_id, amount, claim_date, vendor_name, currency).
    """
    with get_connection() as conn:
        rows = safe_query(conn, """
            SELECT
                employee_id,
                currency,
                COALESCE(vendor_name, 'Unknown') AS vendor_name,
                claim_date::date AS dt,
                amount::float AS amount,
                COUNT(*) AS occurrences,
                ARRAY_AGG(claim_id ORDER BY claim_id) AS claim_ids
            FROM expense_claims
            GROUP BY employee_id, currency, COALESCE(vendor_name, 'Unknown'), claim_date::date, amount
            HAVING COUNT(*) >= %s
            ORDER BY occurrences DESC, dt DESC
        """, (threshold,))
        for r in rows:
            r["amount"] = float(r["amount"] or 0.0)
            r["occurrences"] = int(r["occurrences"] or 0)
        return {"duplicates": rows}


def get_amount_distribution(buckets: List[int]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Histogram of amounts for custom bucket cutoffs.
    Example buckets: [0,100,500,1000,5000,10000] => ranges 0-100,100-500,500-1000,1000-5000,5000-10000,10000+
    """
    if not buckets or len(buckets) < 2:
        return {"buckets": [], "counts": []}

    # Build labels and param pairs
    ranges = []
    params: list = []
    for i in range(len(buckets) - 1):
        a, b = buckets[i], buckets[i + 1]
        label = f"{a}-{b}"
        ranges.append((label, a, b))
    last_label = f"{buckets[-1]}+"

    # Build SUM(CASE ...) fragments using parameters
    sum_cases = []
    for idx, (_label, a, b) in enumerate(ranges):
        sum_cases.append(f"SUM(CASE WHEN amount >= %s AND amount < %s THEN 1 ELSE 0 END) AS b{idx}")
        params.extend([a, b])
    # last open-ended bucket
    sum_cases.append(f"SUM(CASE WHEN amount >= %s THEN 1 ELSE 0 END) AS b_last")
    params.append(buckets[-1])

    sql = f"SELECT {', '.join(sum_cases)} FROM expense_claims"

    with get_connection() as conn:
        row = safe_query(conn, sql, tuple(params))
        if not row:
            return {"buckets": [], "counts": []}
        counts: List[int] = []
        for i in range(len(ranges)):
            counts.append(int(row[0].get(f"b{i}", 0) or 0))
        counts.append(int(row[0].get("b_last", 0) or 0))

    labels = [r[0] for r in ranges] + [last_label]
    return {"buckets": labels, "counts": counts}


def get_pending_aging() -> Dict[str, List[Dict[str, Any]]]:
    """
    For pending-like statuses, compute age in days since claim_date.
    """
    pending_statuses = ("Pending", "Pending Review", "Manager Pending", "Finance Pending")
    with get_connection() as conn:
        rows = safe_query(conn, f"""
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
            WHERE status = ANY(%s)
            ORDER BY age_days DESC, claim_date ASC
            LIMIT 500
        """, (list(pending_statuses),))
        for r in rows:
            if r.get("amount") is not None:
                r["amount"] = float(r["amount"])
            r["age_days"] = int(r.get("age_days", 0) or 0)
        return {"pending": rows}


def get_claim_details(claim_id: str) -> Dict[str, Any] | None:
    """
    One claim with joined employee basics.
    """
    with get_connection() as conn:
        rows = safe_query(conn, """
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
            WHERE c.claim_id = %s
            LIMIT 1
        """, (claim_id,))
        if not rows:
            return None
        row = rows[0]
        if "amount" in row and row["amount"] is not None:
            row["amount"] = float(row["amount"])
        return row


# Optional: expose a graceful shutdown for the pool if your app wants to call it.
def shutdown_pool():
    close_connection_pool()


__all__ = [
    "get_all_claims",
    "get_total_claims",
    "get_total_amount",
    "get_fraud_stats",
    "get_auto_approved_rate",
    "get_avg_amount_per_employee",
    "get_top_vendors",
    "get_claims_by_category",
    "get_table_health",
    "get_claims_summary",
    "get_auto_approved_count",
    "get_claims_by_date",
    "get_automation_rate_by_date",
    "get_processing_time_by_date",
    "get_avg_processing_time_by_date",
    "get_claims_by_department",
    "get_top_employees",
    "get_fraud_flags",
    "get_duplicates",
    "get_amount_distribution",
    "get_pending_aging",
    "get_claim_details",
    "shutdown_pool",
]
