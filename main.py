# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from db import get_connection
import queries
from datetime import date
from typing import Optional

app = FastAPI(
    title="Claims Analytics API",
    description="Backend API for Claims Management KPIs and Dashboards",
    version="1.0.0"
)

# --- CORS Setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health check ---
@app.get("/health", tags=["System"])
def health_check(conn=Depends(get_connection)):
    """Check if DB tables exist and return API health."""
    try:
        status = queries.get_table_health(conn)
        return {"status": "ok", "db_tables": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Core KPI Endpoints ---
@app.get("/claims/summary", tags=["KPIs"])
def claims_summary(conn=Depends(get_connection)):
    """Get overall summary stats for claims."""
    return queries.get_claims_summary(conn)


@app.get("/claims/processing-time", tags=["KPIs"])
def avg_processing_time(conn=Depends(get_connection)):
    """Get average processing time (in hours) across all processed claims."""
    return queries.get_avg_processing_time(conn)


@app.get("/claims/by-date", tags=["Trends"])
def claims_by_date(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    conn=Depends(get_connection)
):
    """Get daily total claims and total amount within a date range."""
    return queries.get_claims_by_date(conn, start_date, end_date)


@app.get("/claims/automation-rate", tags=["Trends"])
def automation_rate_by_date(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    conn=Depends(get_connection)
):
    """Get automation rate trend (auto-approved vs total claims)."""
    return queries.get_automation_rate_by_date(conn, start_date, end_date)


@app.get("/claims/processing-time-trend", tags=["Trends"])
def processing_time_by_date(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    conn=Depends(get_connection)
):
    """Get average claim processing time trend by date."""
    return queries.get_processing_time_by_date(conn, start_date, end_date)


# --- Breakdown & Insights ---
@app.get("/claims/by-department", tags=["Insights"])
def claims_by_department(limit: int = 20, conn=Depends(get_connection)):
    """Get department-level claim stats."""
    return queries.get_claims_by_department(conn, limit)


@app.get("/claims/top-employees", tags=["Insights"])
def top_employees(limit: int = 20, conn=Depends(get_connection)):
    """Get top employees by total claim amount."""
    return queries.get_top_employees(conn, limit)


@app.get("/claims/fraud-flags", tags=["Insights"])
def fraud_flags(limit: int = 50, offset: int = 0, conn=Depends(get_connection)):
    """Get flagged claims with fraud risk details."""
    return queries.get_fraud_flags(conn, limit, offset)


@app.get("/claims/duplicates", tags=["Insights"])
def duplicate_claims(threshold: int = 2, conn=Depends(get_connection)):
    """Detect potential duplicate claims."""
    return queries.get_duplicates(conn, threshold)


@app.get("/claims/amount-distribution", tags=["Insights"])
def amount_distribution(conn=Depends(get_connection)):
    """Distribution of claims by amount range."""
    return queries.get_amount_distribution(conn)


@app.get("/claims/pending-aging", tags=["Insights"])
def pending_claims_aging(conn=Depends(get_connection)):
    """Get pending claims aging distribution."""
    return queries.get_pending_aging(conn)


@app.get("/claims/{claim_id}", tags=["Details"])
def claim_details(claim_id: int, conn=Depends(get_connection)):
    """Get full details of a single claim by ID."""
    claim = queries.get_claim_details(conn, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


# --- Root Redirect ---
@app.get("/", include_in_schema=False)
def root():
    return {"message": "Welcome to the Claims Analytics API. Visit /docs for API documentation."}
