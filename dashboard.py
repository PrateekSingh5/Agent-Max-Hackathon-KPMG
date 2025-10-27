# dashboard.py
import streamlit as st
import pandas as pd
import requests
from datetime import date
import plotly.express as px

API_BASE_URL = "http://localhost:8000"  # update as needed
st.set_page_config(page_title="Claims Analytics Dashboard", layout="wide")


# -------------------------
# Helpers
# -------------------------
def fetch_api(endpoint, params=None):
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.error(f"⚠️ Failed to fetch {endpoint}: {e}")
    return None


def normalize_list_response(payload, candidate_keys=None):
    """
    Normalize a JSON response to a list of dicts (rows).
    payload may be:
     - a list of dicts -> returned as-is
     - a dict with a single key mapping to list -> return that list
     - a dict with known wrapper keys -> returns payload[wrapper]
    """
    if payload is None:
        return []

    # already a list of rows
    if isinstance(payload, list):
        return payload

    # payload is a dict: try to find the list inside
    if isinstance(payload, dict):
        # if there's an obvious key containing a list, return it
        for k, v in payload.items():
            if isinstance(v, list):
                return v

        # fallback: look for known wrapper keys (common)
        known_wrappers = ['by_date', 'data', 'results', 'rows']
        for k in known_wrappers:
            if k in payload and isinstance(payload[k], list):
                return payload[k]

    # nothing found
    return []


def find_date_column(df: pd.DataFrame):
    """
    Return the date-like column name from a dataframe, or None.
    Checks common names: claim_date, day, date, by_date, claimDate, etc.
    """
    candidates = ['claim_date', 'day', 'date', 'by_date', 'claimDate', 'claimdate']
    cols = [c.lower() for c in df.columns]
    for cand in candidates:
        if cand in cols:
            # return original-case column name
            return df.columns[cols.index(cand)]
    # try to detect a datetime-like column
    for c in df.columns:
        # try convert first non-null value to datetime
        sample = df[c].dropna()
        if not sample.empty:
            try:
                pd.to_datetime(sample.iloc[0])
                return c
            except Exception:
                continue
    return None


# -------------------------
# Sidebar filters
# -------------------------
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start date", value=date(2025, 1, 1))
end_date = st.sidebar.date_input("End date", value=date.today())
st.sidebar.markdown("---")
st.sidebar.caption("Adjust to filter time-range.")

# -------------------------
# Title & KPIs
# -------------------------
st.title("📊 Claims Management Analytics Dashboard")

summary = fetch_api("/claims/summary")
if summary:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Claims", summary.get("total_claims", 0))
    col2.metric("Auto Approved", summary.get("auto_approved", 0))
    col3.metric("Pending", summary.get("pending_claims", 0))
    col4.metric("Fraud Flags", summary.get("fraud_flags", 0))
    avg_amt = summary.get("avg_claim_amount", summary.get("avg_amount", 0) or 0)
    col5.metric("Avg Claim Amount", f"₹{float(avg_amt):,.2f}")

st.markdown("---")


# -------------------------
# Claims by date (time-series)
# -------------------------
st.subheader("Claims by Date")
raw = fetch_api("/claims/by-date", params={"start_date": start_date, "end_date": end_date})
rows = normalize_list_response(raw)

if not rows:
    st.info("No claims-by-date data available for the selected range.")
else:
    df = pd.DataFrame(rows)

    # Handle nested or wrapper responses
    if 'by_date' in df.columns and df['by_date'].apply(lambda x: isinstance(x, dict)).any():
        df = pd.json_normalize(df['by_date'])

    # Detect the actual date column name dynamically
    date_col = None
    for col in df.columns:
        if any(k in col.lower() for k in ["date", "day"]):
            date_col = col
            break

    # If no date column found, but "by_date" exists, use that
    if date_col is None and "by_date" in df.columns:
        date_col = "by_date"

    # Rename the date column to "claim_date" for consistency
    df = df.rename(columns={date_col: "claim_date"})

    # Now detect y-axis column
    if "total_claims" not in df.columns:
        # look for numeric-like alternatives
        for col in df.columns:
            if any(k in col.lower() for k in ["count", "claims", "total"]):
                df = df.rename(columns={col: "total_claims"})
                break

    # Plot
    if "claim_date" in df.columns and "total_claims" in df.columns:
        df["claim_date"] = pd.to_datetime(df["claim_date"], errors="coerce").dt.date
        df = df.sort_values("claim_date")
        fig = px.bar(df, x="claim_date", y="total_claims", title="Claims Submitted per Day", text="total_claims")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"❌ Missing required columns in data. Found: {list(df.columns)}")



# -------------------------
# Automation rate
# -------------------------
st.subheader("Automation Rate Over Time")
raw_auto = fetch_api("/claims/automation-rate", params={"start_date": start_date, "end_date": end_date})
rows_auto = normalize_list_response(raw_auto)
if not rows_auto:
    st.info("No automation-rate data available.")
else:
    df_auto = pd.DataFrame(rows_auto)
    # sometimes column is 'day' or 'claim_date'
    date_col = find_date_column(df_auto)
    if date_col is None:
        st.error("Couldn't detect a date column in /claims/automation-rate response.")
    else:
        df_auto[date_col] = pd.to_datetime(df_auto[date_col]).dt.date
        # rename automation column variants
        if 'automation_rate' not in df_auto.columns and 'rate' in df_auto.columns:
            df_auto = df_auto.rename(columns={'rate': 'automation_rate'})
        if 'automation_rate' not in df_auto.columns:
            st.error("No 'automation_rate' column found; available: " + ", ".join(df_auto.columns))
        else:
            df_auto = df_auto.sort_values(by=date_col)
            fig2 = px.line(df_auto, x=date_col, y='automation_rate', title="Automation Rate by Date", markers=True)
            st.plotly_chart(fig2, use_container_width=True)


# -------------------------
# Claims by category
# -------------------------
st.subheader("Claims by Category")
cat_raw = fetch_api("/claims/by-category")
cat_rows = normalize_list_response(cat_raw)
if cat_rows:
    df_cat = pd.DataFrame(cat_rows)
    if 'expense_category' not in df_cat.columns and 'category' in df_cat.columns:
        df_cat = df_cat.rename(columns={'category': 'expense_category'})
    if 'total_amount' not in df_cat.columns and 'sum' in df_cat.columns:
        df_cat = df_cat.rename(columns={'sum': 'total_amount'})
    fig3 = px.bar(df_cat, x='expense_category', y='total_amount', title="Amount by Category", text='total_amount')
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No category data available.")


# -------------------------
# Top vendors
# -------------------------
st.subheader("Top Vendors")
vendors = fetch_api("/claims/by-vendor", params={"limit": 10})
vendors = normalize_list_response(vendors)
if vendors:
    df_v = pd.DataFrame(vendors)
    if 'vendor_name' in df_v.columns and 'total_amount' in df_v.columns:
        fig4 = px.bar(df_v.head(10), x='vendor_name', y='total_amount', title="Top Vendors by Amount", text='total_amount')
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.dataframe(df_v)
else:
    st.info("No vendor data available.")


# -------------------------
# Pending aging
# -------------------------
st.subheader("Pending Claims Aging")
pending = fetch_api("/claims/pending-aging")
if pending and isinstance(pending, dict):
    # present as simple table
    df_pending = pd.DataFrame([pending]).T.reset_index()
    df_pending.columns = ['bucket', 'count']
    st.bar_chart(df_pending.set_index('bucket')['count'])
else:
    st.info("No pending-aging data available.")


st.markdown("---")
st.caption("© 2025 Claims Analytics Dashboard — Powered by FastAPI + Streamlit")
