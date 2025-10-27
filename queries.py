# queries.py
"""
Database query layer for Agent Max Finance System.
Each function returns Python-native data (list[dict]) using safe_query().
"""

from datetime import date
from typing import Optional
from db import get_connection, safe_query


# -------------------------------------------------------
# Helper for uniform execution
# -------------------------------------------------------
def _read(query: str, params: Optional[tuple] = None):
    """Executes a query safely and returns list of dicts."""
    with get_connection() as conn:
        return safe_query(conn, query, params)


# -------------------------------------------------------
# Claims summary / KPIs
# -------------------------------------------------------
def get_claims_summary(start_date: Optional[date] = None, end_date: Optional[date] = None):
    if start_date and end_date:
        sql = """
            SELECT
                COUNT(*)::int AS total_claims,
                COALESCE(SUM(amount)::float,0) AS total_amount,
                SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END)::int AS approved,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END)::int AS rejected,
                SUM(CASE WHEN status = 'Auto Approved' THEN 1 ELSE 0 END)::int AS auto_approved,
                SUM(CASE WHEN status = 'Finance Pending' THEN 1 ELSE 0 END)::int AS finance_pending,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END)::int AS manager_pending,
                COALESCE(AVG(amount)::float,0) AS avg_amount
            FROM expense_claims
            WHERE claim_date BETWEEN %s AND %s;
        """
        return _read(sql, (start_date, end_date))
    else:
        sql = """
            SELECT
                COUNT(*)::int AS total_claims,
                COALESCE(SUM(amount)::float,0) AS total_amount,
                SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END)::int AS approved,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END)::int AS rejected,
                SUM(CASE WHEN status = 'Auto Approved' THEN 1 ELSE 0 END)::int AS auto_approved ,
                SUM(CASE WHEN status = 'Finance Pending' THEN 1 ELSE 0 END)::int AS finance_pending,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END)::int AS manager_pending,
                COALESCE(AVG(amount)::float,0) AS avg_amount
            FROM expense_claims
        """
        return _read(sql)


# -------------------------------------------------------
# Monthly trends
# -------------------------------------------------------
def get_monthly_trend(start_date: date, end_date: date):
    sql = """
        SELECT DATE_TRUNC('month', claim_date)::date AS month,
               COALESCE(SUM(amount)::float,0) AS total_amount,
               COUNT(*)::int AS claim_count
        FROM expense_claims
        WHERE claim_date BETWEEN %s AND %s
        GROUP BY 1
        ORDER BY 1;
    """
    return _read(sql, (start_date, end_date))


# -------------------------------------------------------
# Top vendors
# -------------------------------------------------------
def get_top_vendors(start_date: date, end_date: date, limit: int = 10):
    sql = """
        SELECT COALESCE(vendor_name,'(unknown)') AS vendor_name,
               COALESCE(SUM(amount)::float,0) AS total_amount,
               COUNT(*)::int AS claim_count
        FROM expense_claims
        WHERE claim_date BETWEEN %s AND %s
        GROUP BY vendor_name
        ORDER BY total_amount DESC
        LIMIT %s;
    """
    return _read(sql, (start_date, end_date, limit))


# -------------------------------------------------------
# Fraud claims
# -------------------------------------------------------
def get_fraud_claims(start_date: date, end_date: date):
    sql = """
        SELECT claim_id, employee_id, claim_date, expense_category,
               amount::float, currency, vendor_name, status, details
        FROM expense_claims
        WHERE fraud_flag = TRUE AND claim_date BETWEEN %s AND %s
        ORDER BY claim_date DESC
        LIMIT 1000;
    """
    return _read(sql, (start_date, end_date))


# -------------------------------------------------------
# Pending claims
# -------------------------------------------------------
def get_pending_claims(start_date: date, end_date: date):
    sql = """
        SELECT claim_id, employee_id, claim_date, expense_category,
               amount::float, currency, vendor_name, status
        FROM expense_claims
        WHERE status ILIKE 'Pending' AND claim_date BETWEEN %s AND %s
        ORDER BY claim_date DESC
        LIMIT 1000;
    """
    return _read(sql, (start_date, end_date))


# -------------------------------------------------------
# Full claims list
# -------------------------------------------------------
def get_claims_list(start_date: date, end_date: date, status: Optional[str] = None,
                    employee_id: Optional[str] = None, limit: int = 500):
    base_sql = """
        SELECT c.id, c.claim_id, c.employee_id,
               (e.first_name || ' ' || e.last_name) AS employee_name,
               c.claim_date, c.expense_category, c.amount::float, c.currency, c.vendor_name,
               c.payment_mode, c.status, c.auto_approved, c.is_duplicate, c.fraud_flag, c.details
        FROM expense_claims c
        LEFT JOIN employees e ON c.employee_id = e.employee_id
        WHERE c.claim_date BETWEEN %s AND %s
    """
    params = [start_date, end_date]
    if status:
        base_sql += " AND c.status = %s"
        params.append(status)
    if employee_id:
        base_sql += " AND c.employee_id = %s"
        params.append(employee_id)
    base_sql += " ORDER BY c.claim_date DESC LIMIT %s;"
    params.append(limit)
    return _read(base_sql, tuple(params))


# -------------------------------------------------------
# Policy compliance
# -------------------------------------------------------
def get_policy_compliance():
    # Based on your schema: expense_policies(category, max_allowance)
    sql = """
        SELECT
            p.policy_id,
            p.category AS policy_category,
            p.max_allowance::float AS max_allowance,
            COUNT(DISTINCT c.claim_id)::int AS total_claims,
            SUM(CASE WHEN c.amount > p.max_allowance THEN 1 ELSE 0 END)::int AS violations,
            SUM(CASE WHEN c.amount > p.max_allowance THEN (c.amount - p.max_allowance) ELSE 0 END)::float AS total_excess
        FROM expense_claims c
        JOIN expense_policies p ON c.expense_category = p.category
        GROUP BY p.policy_id, p.category, p.max_allowance
        ORDER BY violations DESC;
    """
    return _read(sql)
