
# # dashboard.py
# """
# Streamlit enterprise-level finance dashboard that uses the FastAPI backend endpoints.
# Single 'Report' tab with two rows of slicers at the top, then KPIs, charts, and table.
# """

# import os
# import io
# from datetime import date, timedelta
# from typing import List, Optional  # <-- important for Python 3.8/3.9

# import pandas as pd
# import plotly.express as px
# import requests
# import streamlit as st
# from dotenv import load_dotenv

# # ── Streamlit page config MUST be first ────────────────────────────────────────
# st.set_page_config(
#     page_title="Finance Dashboard — Agent Max",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# load_dotenv()

# DB_CONFIG = {
#     "host": os.getenv("DB_HOST", "localhost"),
#     "port": os.getenv("DB_PORT", "5432"),
#     "database": os.getenv("DB_NAME", "agent_max"),
#     "user": os.getenv("DB_USER", "myuser"),
#     "password": os.getenv("DB_PASSWORD", "mypassword"),
# }

# # --- configure your API base (match uvicorn host/port) ---
# API_BASE = "http://localhost:8000"
# TIMEOUT = 10


# # -------------------------
# # HTTP / API helpers
# # -------------------------
# # @st.cache_data(ttl=3)
# def api_get(endpoint: str, params: dict = None):
#     url = f"{API_BASE}{endpoint}"
#     try:
#         r = requests.get(url, params=params or {}, timeout=TIMEOUT)
#         r.raise_for_status()
#         # Defensive: some endpoints may return empty body
#         try:
#             return r.json()
#         except Exception:
#             return []
#     except Exception as e:
#         st.error(f"API error: {url} — {e}")
#         return []


# def to_df(obj):
#     try:
#         return pd.DataFrame(obj)
#     except Exception:
#         return pd.DataFrame()


# # -------------------------
# # Data loaders (API-backed)
# # -------------------------
# # @st.cache_data(ttl=3)
# def load_claims(start_date: date, end_date: date, filters: dict):
#     params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
#     if filters.get("employee_id"):
#         params["employee_id"] = filters["employee_id"]
#     if filters.get("status"):
#         params["status"] = filters["status"]
#     data = api_get("/claims/list", params=params)
#     return to_df(data)

# #
# # @st.cache_data(ttl=3)
# def load_summary(start_date: date = None, end_date: date = None, filters: dict = None):
#     if start_date and end_date:
#         params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
#         data = api_get("/claims/summary", params=params)
#     else:
#         data = api_get("/claims/summary")

#     if isinstance(data, list) and len(data) > 0:
#         summary = data[0]
#     elif isinstance(data, dict):
#         summary = data
#     else:
#         summary = {}

#     summary = {
#         "total_claims": summary.get("total_claims", 0),
#         "total_amount": summary.get("total_amount", 0.0),
#         "approved": summary.get("approved", 0),
#         "rejected": summary.get("rejected", 0),
#         "auto_approved": summary.get("auto_approved", 0),
#         "duplicates": summary.get("duplicates", 0),
#         "avg_amount": summary.get("avg_amount", 0.0),
#         "finance_pending": summary.get("finance_pending", 0.0),
#         "manager_pending": summary.get("manager_pending", 0.0),
#     }
#     return summary


# # @st.cache_data(ttl=3)
# def load_monthly_trend(start_date: date, end_date: date, filters: dict):
#     params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
#     data = api_get("/claims/monthly_trend", params=params)
#     df = to_df(data)
#     return df.sort_values("month") if not df.empty else df


# # @st.cache_data(ttl=3)
# def load_top_vendors(start_date: date, end_date: date, filters: dict, limit=10):
#     params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "limit": limit}
#     data = api_get("/claims/top_vendors", params=params)
#     return to_df(data)


# # @st.cache_data(ttl=3)
# def load_policy_compliance():
#     data = api_get("/claims/policy_compliance")
#     return to_df(data)


# # -------------------------
# # UI helpers
# # -------------------------
# def kpi_column(label: str, value, delta=None, subtitle=None):
#     st.markdown(
#         f"""
#         <div style="padding:10px;border-radius:8px;background:#f6f8fa;">
#           <div style="font-size:14px;color:#6b7280">{label}</div>
#           <div style="font-size:22px;font-weight:700;margin-top:6px">{value}</div>
#           {"<div style='font-size:12px;color:#10b981;margin-top:4px;'>+" + str(delta) + "</div>" if delta is not None else ""}
#           {"<div style='font-size:12px;color:#6b7280;margin-top:4px;'>" + subtitle + "</div>" if subtitle else ""}
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )


# def df_to_csv_bytes(df: pd.DataFrame):
#     buf = io.BytesIO()
#     df.to_csv(buf, index=False)
#     buf.seek(0)
#     return buf.getvalue()


# def apply_client_side_filters(df: pd.DataFrame, filters: dict, status_list: Optional[List[str]]):
#     if df.empty:
#         return df
#     out = df.copy()

#     if "expense_category" in filters:
#         out = out[out["expense_category"] == filters["expense_category"]]

#     if "currency" in filters:
#         out = out[out["currency"] == filters["currency"]]

#     if "vendor_name" in filters and filters["vendor_name"]:
#         needle = str(filters["vendor_name"]).strip().lower()
#         out = out[out["vendor_name"].fillna("").str.lower().str.contains(needle)]

#     if status_list:
#         out = out[out["status"].fillna("").isin(status_list)]

#     return out


# # -------------------------
# # Main Streamlit app
# # -------------------------
# def main():
#     (tab_report,) = st.tabs(["Report"])

#     with tab_report:
#         # ------------- SLICERS (2 rows) -------------
#         today = date.today()
#         default_start = today - timedelta(days=365)

#         # Row 1: Dates + Employee
#         r1c1, r1c2, r1c3, r1c4 = st.columns([1.1, 1.1, 1.2, 0.6])
#         with r1c1:
#             start_date = st.date_input("Start date", default_start, key="rep_start")
#         with r1c2:
#             end_date = st.date_input("End date", today, key="rep_end")

#         # Pull sample to populate dropdowns (handle empty safely)
#         sample_claims = load_claims(start_date, end_date, {})
#         employee_list = sorted(sample_claims["employee_id"].dropna().unique().tolist()) if not sample_claims.empty else []
#         category_list = sorted(sample_claims["expense_category"].dropna().unique().tolist()) if not sample_claims.empty else []
#         currency_list = sorted(sample_claims["currency"].dropna().unique().tolist()) if not sample_claims.empty else []

#         with r1c3:
#             employee_choice = st.selectbox("Employee", options=["All"] + employee_list, index=0, key="rep_emp")
#         with r1c4:
#             st.write("")  # spacer
#             st.write("")

#         # Row 2: Category + Currency + Vendor + Status
#         r2c1, r2c2, r2c3, r2c4 = st.columns([1.1, 1.1, 1.4, 2.4])
#         with r2c1:
#             category_choice = st.selectbox("Category", options=["All"] + category_list, index=0, key="rep_cat")
#         with r2c2:
#             currency_choice = st.selectbox("Currency", options=["All"] + currency_list, index=0, key="rep_cur")
#         with r2c3:
#             vendor_search = st.text_input("Vendor contains", key="rep_vendor")
#         with r2c4:
#             status_choice = st.multiselect(
#                 "Status",
#                 options=["Pending", "Manager Pending", "Finance Pending", "Pending Review", "Approved", "Rejected", "Processed"],
#                 default=["Pending", "Manager Pending", "Finance Pending", "Pending Review", "Approved", "Rejected", "Processed"],
#                 key="rep_status",
#             )

#         st.markdown("---")

#         # Build filters dict (server-side for supported keys, rest client-side)
#         filters = {}
#         if employee_choice and employee_choice != "All":
#             filters["employee_id"] = employee_choice
#         if category_choice and category_choice != "All":
#             filters["expense_category"] = category_choice
#         if currency_choice and currency_choice != "All":
#             filters["currency"] = currency_choice
#         if vendor_search:
#             filters["vendor_name"] = vendor_search

#         # ------------- LOAD DATA -------------
#         with st.spinner("Loading report..."):
#             df_claims_raw = load_claims(start_date, end_date, filters)
#             df_claims = apply_client_side_filters(df_claims_raw, filters, status_choice)

#             summary = load_summary(start_date, end_date, filters)
#             monthly = load_monthly_trend(start_date, end_date, filters)
#             top_vendors = load_top_vendors(start_date, end_date, filters, limit=10)
#             policy_df = load_policy_compliance()

#             pending_statuses = {"Pending", "Manager Pending", "Finance Pending", "Pending Review"}
#             if df_claims.empty or "status" not in df_claims.columns:
#                 pending_df = pd.DataFrame(
#                     columns=["claim_id", "employee_id", "claim_date", "expense_category", "amount", "currency", "vendor_name", "status"]
#                 )
#             else:
#                 pending_df = df_claims[df_claims["status"].fillna("").str.strip().isin(pending_statuses)].copy()

#         # ------------- KPIs -------------
#         st.markdown("### KPIs")
#         k1, k2, k3, k4, k5, k6 = st.columns(6)
#         with k1:
#             kpi_column("Total Claims", f"{summary['total_claims']:,}")
#         with k2:
#             kpi_column("Total Amount", f"₹{int(summary['total_amount']):,}")
#         with k3:
#             kpi_column("Avg Claim Amount", f"₹{int(summary['avg_amount']):,}")
#         with k4:
#             kpi_column("Auto-approved", f"{summary['auto_approved']:,}")
#         with k5:
#             kpi_column("Manager Pending", f"{summary['manager_pending']:,}")
#         with k6:
#             kpi_column("Finance Pending", f"{summary['finance_pending']:,}")

#         st.markdown("---")

#         # ------------- VISUALS -------------
#         left, right = st.columns([3, 1.3])

#         with left:
#             st.subheader("Monthly Expense Trend")
#             if monthly.empty:
#                 st.info("No data available for selected date range/filters.")
#             else:
#                 monthly_plot = monthly.copy()
#                 if "month" in monthly_plot.columns:
#                     monthly_plot["month"] = pd.to_datetime(monthly_plot["month"], errors="coerce")
#                 fig = px.area(
#                     monthly_plot.dropna(subset=["month"]),
#                     x="month",
#                     y="total_amount",
#                     title="Total Expense by Month",
#                     markers=True,
#                 )
#                 fig.update_layout(yaxis_title="Amount", xaxis_title="Month")
#                 st.plotly_chart(fig, use_container_width=True)

#             st.subheader("Top Vendors")
#             if top_vendors.empty:
#                 st.write("No vendor data available.")
#             else:
#                 fig2 = px.bar(
#                     top_vendors,
#                     x="vendor_name",
#                     y="total_amount",
#                     title="Top Vendors (by amount)",
#                     text="claim_count",
#                 )
#                 fig2.update_layout(xaxis_title="Vendor", yaxis_title="Total Amount", xaxis_tickangle=-45)
#                 st.plotly_chart(fig2, use_container_width=True)

#         with right:
#             st.subheader("Pending Claims")
#             if pending_df.empty:
#                 st.write("No pending claims.")
#             else:
#                 pie_df = pending_df.groupby("expense_category", dropna=False).size().reset_index(name="value")
#                 pie_df["expense_category"] = pie_df["expense_category"].fillna("(unknown)")
#                 fig = px.pie(pie_df, names="expense_category", values="value", hole=0.6)
#                 fig.update_traces(textinfo="label+value", hovertemplate="%{label}: %{value}<extra></extra>")
#                 fig.update_layout(
#                     title={"text": "Pending Claims by Category"},
#                     margin=dict(t=30, b=10, l=10, r=10),
#                     showlegend=True,
#                 )
#                 st.plotly_chart(fig, use_container_width=True)

#         # ------------- TABLE + EXPORT -------------
#         st.markdown("---")
#         st.subheader("Claims Table")
#         if df_claims.empty:
#             st.write("No claims found for this filter set.")
#         else:
#             with st.expander("Table options"):
#                 cols = st.multiselect("Columns to show", options=list(df_claims.columns), default=list(df_claims.columns))
#                 page_size = st.number_input("Rows per page", min_value=5, max_value=200, value=25)

#             st.dataframe(
#                 df_claims[cols].sort_values("claim_date", ascending=False).reset_index(drop=True),
#                 height=500,
#                 use_container_width=True,
#             )

#             csv_bytes = df_to_csv_bytes(df_claims[cols])
#             st.download_button(
#                 label="Download filtered as CSV",
#                 data=csv_bytes,
#                 file_name="claims_filtered.csv",
#                 mime="text/csv",
#             )


# # Ensure app runs in Streamlit
# if __name__ == "__main__":
#     main()





# dashboard.py
"""
Streamlit enterprise-level finance dashboard that uses the FastAPI backend endpoints.
Single 'Report' tab with two rows of slicers at the top, then KPIs, charts, and table.
"""

import os
import io
from datetime import date, timedelta
from typing import List, Optional  # <-- important for Python 3.8/3.9

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from dotenv import load_dotenv


import requests
from datetime import date
import streamlit as st

# ── Streamlit page config MUST be first ────────────────────────────────────────
# st.set_page_config(
#     page_title="Finance Dashboard — Agent Max",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "agent_max"),
    "user": os.getenv("DB_USER", "myuser"),
    "password": os.getenv("DB_PASSWORD", "mypassword"),
}

# --- configure your API base (match uvicorn host/port) ---
API_BASE = "http://localhost:8000"
TIMEOUT = 10


# -------------------------
# HTTP / API helpers
# -------------------------
# @st.cache_data(ttl=3)
def api_get(endpoint: str, params: dict = None):
    url = f"{API_BASE}{endpoint}"
    try:
        r = requests.get(url, params=params or {}, timeout=TIMEOUT)
        r.raise_for_status()
        # Defensive: some endpoints may return empty body
        try:
            return r.json()
        except Exception:
            return []
    except Exception as e:
        st.error(f"API error: {url} — {e}")
        return []


def to_df(obj):
    try:
        return pd.DataFrame(obj)
    except Exception:
        return pd.DataFrame()


# -------------------------
# Data loaders (API-backed)
# -------------------------
# @st.cache_data(ttl=3)
def load_claims(start_date: date, end_date: date, filters: dict):
    params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
    if filters.get("employee_id"):
        params["employee_id"] = filters["employee_id"]
    if filters.get("status"):
        params["status"] = filters["status"]
    data = api_get("/claims/list", params=params)
    return to_df(data)

#
# @st.cache_data(ttl=3)
def load_summary(start_date: date = None, end_date: date = None, filters: dict = None):
    if start_date and end_date:
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = api_get("/claims/summary", params=params)
    else:
        data = api_get("/claims/summary")

    if isinstance(data, list) and len(data) > 0:
        summary = data[0]
    elif isinstance(data, dict):
        summary = data
    else:
        summary = {}

    summary = {
        "total_claims": summary.get("total_claims", 0),
        "total_amount": summary.get("total_amount", 0.0),
        "approved": summary.get("approved", 0),
        "rejected": summary.get("rejected", 0),
        "auto_approved": summary.get("auto_approved", 0),
        "avg_amount": summary.get("avg_amount", 0.0),
        "finance_pending": summary.get("finance_pending", 0.0),
        "manager_pending": summary.get("manager_pending", 0.0),
    }
    return summary


# @st.cache_data(ttl=3)
def load_monthly_trend(start_date: date, end_date: date, filters: dict):
    params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
    data = api_get("/claims/monthly_trend", params=params)
    df = to_df(data)
    return df.sort_values("month") if not df.empty else df


# @st.cache_data(ttl=3)
def load_top_vendors(start_date: date, end_date: date, filters: dict, limit=10):
    params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "limit": limit}
    data = api_get("/claims/top_vendors", params=params)
    return to_df(data)


# @st.cache_data(ttl=3)
def load_policy_compliance():
    data = api_get("/claims/policy_compliance")
    return to_df(data)


# -------------------------
# UI helpers
# -------------------------

# def kpi_column(label: str, value, delta=None, subtitle=None):
#     st.markdown(
#         f"""
#         <div style="padding:10px;border-radius:8px;background:#f6f8fa;">
#           <div style="font-size:14px;color:#6b7280">{label}</div>
#           <div style="font-size:22px;font-weight:700;margin-top:6px">{value}</div>
#           {"<div style='font-size:12px;color:#10b981;margin-top:4px;'>+" + str(delta) + "</div>" if delta is not None else ""}
#           {"<div style='font-size:12px;color:#6b7280;margin-top:4px;'>" + subtitle + "</div>" if subtitle else ""}
#         </div>
#         """,
#         unsafe_allow_html=True,
#     )

def kpi_column(label: str, value, delta=None, subtitle=None):
    html = f"""
    <div style="
        background-color:#f6f8fa;
        border-radius:10px;
        padding:12px 10px;
        text-align:center;
        box-shadow:0 1px 3px rgba(0,0,0,0.08);
        min-height:80px;">
        <div style="font-size:14px;color:#6b7280;font-weight:500;">{label}</div>
        <div style="font-size:24px;font-weight:700;margin-top:6px;color:#111827;">{value}</div>
        {f"<div style='font-size:12px;color:#10b981;margin-top:4px;'>+{delta}</div>" if delta else ""}
        {f"<div style='font-size:12px;color:#6b7280;margin-top:4px;'>{subtitle}</div>" if subtitle else ""}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# def kpi_column(label, value):
#     st.metric(label=label, value=value)




def df_to_csv_bytes(df: pd.DataFrame):
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf.getvalue()


def apply_client_side_filters(df: pd.DataFrame, filters: dict, status_list: Optional[List[str]]):
    if df.empty:
        return df
    out = df.copy()

    if "expense_category" in filters:
        out = out[out["expense_category"] == filters["expense_category"]]

    if "currency" in filters:
        out = out[out["currency"] == filters["currency"]]

    if "vendor_name" in filters and filters["vendor_name"]:
        needle = str(filters["vendor_name"]).strip().lower()
        out = out[out["vendor_name"].fillna("").str.lower().str.contains(needle)]

    if status_list:
        out = out[out["status"].fillna("").isin(status_list)]

    return out

import streamlit as st
import plotly.graph_objects as go

def render_status_distribution(summary: dict):
    """
    Renders an enterprise-style donut chart of claim status distribution
    consistent with the design of other Plotly charts in your app.
    """

    # Prepare data
    status_data = {
        "Status": ["Approved", "Rejected", "Auto Approved", "Finance Pending", "Manager Pending"],
        "Count": [
            summary.get("approved", 0),
            summary.get("rejected", 0),
            summary.get("auto_approved", 0),
            summary.get("finance_pending", 0),
            summary.get("manager_pending", 0)
        ],
    }

    pie_df = pd.DataFrame(status_data)
    pie_df = pie_df[pie_df["Count"] > 0]  # remove zero-count statuses

    if pie_df.empty:
        st.info("No claim status data available.")
        return

    # Create donut chart
    fig = px.pie(
        pie_df,
        names="Status",
        values="Count",
        hole=0.6,
        color="Status",
        color_discrete_map={
            "Approved": "#16a34a",        # green
            "Rejected": "#dc2626",        # red
            "Auto Approved": "#3b82f6",   # blue
            "Finance Pending": "#f59e0b", # amber
            "Manager Pending": "#6b7280"  # gray
        },
    )

    # Update trace visuals
    fig.update_traces(
        textinfo="label+value",
        hovertemplate="%{label}: %{value} claims<extra></extra>",
        textfont_size=13,
        marker=dict(line=dict(color="#ffffff", width=2))
    )

    # Add total in center
    total_claims = int(pie_df["Count"].sum())
    fig.add_annotation(
        text=f"<b>{total_claims}</b><br>Total Claims",
        x=0.5,
        y=0.5,
        font=dict(size=16, color="#111827"),
        showarrow=False
    )

    # Layout customization
    fig.update_layout(
        title={
            "text": "Claim Status Distribution",
            "x": 0.5,
            "xanchor": "center",
            "font": dict(size=18, color="#111827", family="Inter, sans-serif")
        },
        margin=dict(t=50, b=30, l=10, r=10),
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-0.15,
            x=0.25,
            font=dict(size=12)
        ),
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # Render
    st.plotly_chart(fig, use_container_width=True)




# -------------------------
# Main Streamlit app
# -------------------------
def main():
    (tab_report,) = st.tabs(["Report"])

    with tab_report:
        # ------------- SLICERS (2 rows) -------------
        today = date.today()
        default_start = today - timedelta(days=365)

        # Row 1: Dates + Employee
        r1c1, r1c2, r1c3, r1c4 = st.columns([1.1, 1.1, 1.2, 0.6])
        with r1c1:
            start_date = st.date_input("Start date", default_start, key="rep_start")
        with r1c2:
            end_date = st.date_input("End date", today, key="rep_end")

        # Pull sample to populate dropdowns (handle empty safely)
        sample_claims = load_claims(start_date, end_date, {})
        employee_list = sorted(sample_claims["employee_id"].dropna().unique().tolist()) if not sample_claims.empty else []
        category_list = sorted(sample_claims["expense_category"].dropna().unique().tolist()) if not sample_claims.empty else []
        currency_list = sorted(sample_claims["currency"].dropna().unique().tolist()) if not sample_claims.empty else []

        with r1c3:
            employee_choice = st.selectbox("Employee", options=["All"] + employee_list, index=0, key="rep_emp")
        with r1c4:
            st.write("")  # spacer
            st.write("")

        # Row 2: Category + Currency + Vendor + Status
        r2c1, r2c2, r2c3, r2c4 = st.columns([1.1, 1.1, 1.4, 2.4])
        with r2c1:
            category_choice = st.selectbox("Category", options=["All"] + category_list, index=0, key="rep_cat")
        with r2c2:
            currency_choice = st.selectbox("Currency", options=["All"] + currency_list, index=0, key="rep_cur")
        with r2c3:
            vendor_search = st.text_input("Vendor contains", key="rep_vendor")
        with r2c4:
            status_choice = st.multiselect(
                "Status",
                options=["Pending", "Manager Pending", "Finance Pending", "Pending Review", "Approved", "Rejected", "Processed"],
                default=["Pending", "Manager Pending", "Finance Pending", "Pending Review", "Approved", "Rejected", "Processed"],
                key="rep_status",
            )

        st.markdown("---")

        # Build filters dict (server-side for supported keys, rest client-side)
        filters = {}
        if employee_choice and employee_choice != "All":
            filters["employee_id"] = employee_choice
        if category_choice and category_choice != "All":
            filters["expense_category"] = category_choice
        if currency_choice and currency_choice != "All":
            filters["currency"] = currency_choice
        if vendor_search:
            filters["vendor_name"] = vendor_search

        # ------------- LOAD DATA -------------
        with st.spinner("Loading report..."):
            df_claims_raw = load_claims(start_date, end_date, filters)
            df_claims = apply_client_side_filters(df_claims_raw, filters, status_choice)

            summary = load_summary(start_date, end_date, filters)
            # print(summary)
            monthly = load_monthly_trend(start_date, end_date, filters)
            top_vendors = load_top_vendors(start_date, end_date, filters, limit=10)
            policy_df = load_policy_compliance()

            pending_statuses = {"Pending", "Manager Pending", "Finance Pending", "Pending Review"}
            if df_claims.empty or "status" not in df_claims.columns:
                pending_df = pd.DataFrame(
                    columns=["claim_id", "employee_id", "claim_date", "expense_category", "amount", "currency", "vendor_name", "status"]
                )
            else:
                pending_df = df_claims[df_claims["status"].fillna("").str.strip().isin(pending_statuses)].copy()


        # ------------- KPIs -------------
        st.markdown("### KPIs")

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        

        with k1:
            kpi_column("Total Claims", f"{summary['total_claims']:,}")
        with k2:
            kpi_column("Total Amount", f"₹{int(summary['total_amount']):,}")
        with k3:
            kpi_column("Avg Claim Amount", f"₹{int(summary['avg_amount']):,}")
        with k4:
            kpi_column("Approved", f"{summary['approved']:,}")
        with k5:
            kpi_column("Manager Pending", f"{summary['manager_pending']:,}")
        with k6:
            kpi_column("Finance Pending", f"{summary['finance_pending']:,}")
                
        st.markdown("---")

        # ------------- VISUALS -------------
        left, right = st.columns([3, 1.3])

        with left:
            st.subheader("Monthly Expense Trend")
            if monthly.empty:
                st.info("No data available for selected date range/filters.")
            else:
                monthly_plot = monthly.copy()
                if "month" in monthly_plot.columns:
                    monthly_plot["month"] = pd.to_datetime(monthly_plot["month"], errors="coerce")
                fig = px.area(
                    monthly_plot.dropna(subset=["month"]),
                    x="month",
                    y="total_amount",
                    title="Total Expense by Month",
                    markers=True,
                )
                fig.update_layout(yaxis_title="Amount", xaxis_title="Month")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Top Vendors")
            if top_vendors.empty:
                st.write("No vendor data available.")
            else:
                fig2 = px.bar(
                    top_vendors,
                    x="vendor_name",
                    y="total_amount",
                    title="Top Vendors (by amount)",
                    text="claim_count",
                )
                fig2.update_layout(xaxis_title="Vendor", yaxis_title="Total Amount", xaxis_tickangle=-45)
                st.plotly_chart(fig2, use_container_width=True)

        with right:
            st.subheader("Pending Claims")
            if pending_df.empty:
                st.write("No pending claims.")

            else:
                pie_df = pending_df.groupby("expense_category", dropna=False).size().reset_index(name="value")
                pie_df["expense_category"] = pie_df["expense_category"].fillna("(unknown)")
                fig = px.pie(pie_df, names="expense_category", values="value", hole=0.6)
                fig.update_traces(textinfo="label+value", hovertemplate="%{label}: %{value}<extra></extra>")
                fig.update_layout(
                    title={"text": "Pending Claims by Category"},
                    margin=dict(t=30, b=10, l=10, r=10),
                    showlegend=True,
                )
                st.plotly_chart(fig, use_container_width=True)
    

            st.markdown("### Claim Status Overview")
            render_status_distribution(summary)

        # ------------- TABLE + EXPORT -------------
        st.markdown("---")
        st.subheader("Claims Table")
        if df_claims.empty:
            st.write("No claims found for this filter set.")
        else:
            with st.expander("Table options"):
                cols = st.multiselect("Columns to show", options=list(df_claims.columns), default=list(df_claims.columns))
                page_size = st.number_input("Rows per page", min_value=5, max_value=200, value=25)

            st.dataframe(
                df_claims[cols].sort_values("claim_date", ascending=False).reset_index(drop=True),
                height=500,
                use_container_width=True,
            )

            csv_bytes = df_to_csv_bytes(df_claims[cols])
            st.download_button(
                label="Download filtered as CSV",
                data=csv_bytes,
                file_name="claims_filtered.csv",
                mime="text/csv",
            )



    # -------------------------------------------------------------------
    # AI Finance Insights Section
    # -------------------------------------------------------------------
    st.markdown("## 🤖 AI-Powered Finance Insights")
    st.caption("Autonomous finance intelligence generated from your database by the AI agent.")

    col1, col2 = st.columns(2)
    with col1:
        ai_start_date = st.date_input("Start Date (for AI analysis)", date(2025, 1, 1), key="ai_start")
    with col2:
        ai_end_date = st.date_input("End Date (for AI analysis)", date.today(), key="ai_end")

    if st.button("🚀 Run AI Finance Analysis"):
        with st.spinner("AI Agent analyzing financial data..."):
            try:
                api_url = "http://localhost:8000/api/ai/finance-insights"
                payload = {
                    "start_date": ai_start_date.isoformat(),
                    "end_date": ai_end_date.isoformat(),
                    "include_ai_recommendations": True
                }
                response = requests.post(api_url, json=payload)
                response.raise_for_status()
                ai_data = response.json()
            except Exception as e:
                st.error(f"❌ Error fetching AI insights: {e}")
                st.stop()

        st.success("✅ AI Insights generated successfully")

        # -------------------------------------------------------------------
        # Executive Summary
        # -------------------------------------------------------------------
        st.markdown("### 🧾 Executive Summary")
        st.write(ai_data.get("executive_summary", "No summary available."))

        # -------------------------------------------------------------------
        # Key Metrics Cards
        # -------------------------------------------------------------------
        st.markdown("### 📊 Key Metrics")
        metrics = ai_data.get("key_metrics", {})
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Claims", f"{metrics.get('total_claims', 0):,}")
        c2.metric("Total Spend", f"₹{metrics.get('total_spend', 0):,.0f}")
        c3.metric("Avg Claim", f"₹{metrics.get('avg_claim_amount', 0):,.0f}")
        c4.metric("Auto-Approval %", f"{metrics.get('auto_approval_rate', 0)*100:.1f}%")
        c5.metric("Fraud Flags", f"{metrics.get('fraud_flags', 0):,}")
        c6.metric("Duplicates", f"{metrics.get('duplicates', 0):,}")

        # -------------------------------------------------------------------
        # Insights
        # -------------------------------------------------------------------
        st.markdown("### 💡 AI-Detected Insights")
        insights = ai_data.get("insights", [])
        if insights:
            for i in insights:
                st.markdown(f"- {i}")
        else:
            st.info("No insights detected for this period.")

        # -------------------------------------------------------------------
        # Policy Optimization Suggestions
        # -------------------------------------------------------------------
        st.markdown("### ⚙️ Policy Optimization Suggestions")
        policies = ai_data.get("policy_optimizations", [])
        if policies:
            for p in policies:
                st.markdown(f"- {p}")
        else:
            st.info("No policy optimization suggestions available.")

        # -------------------------------------------------------------------
        # Risk Alerts
        # -------------------------------------------------------------------
        st.markdown("### 🚨 Risk Alerts")
        risks = ai_data.get("risk_alerts", [])
        if risks:
            for r in risks:
                st.markdown(f"- {r}")
        else:
            st.success("No high-risk alerts identified.")

        # -------------------------------------------------------------------
        # Actions
        # -------------------------------------------------------------------
        st.markdown("### 🧠 Recommended Actions")
        actions = ai_data.get("actions", [])
        if actions:
            for a in actions:
                st.markdown(f"- {a}")
        else:
            st.info("No immediate actions recommended.")

        # -------------------------------------------------------------------
        # Recommended Claim-Level Decisions
        # -------------------------------------------------------------------
        st.markdown("### 🧍‍♂️ AI-Recommended Claim Decisions")
        claim_recs = ai_data.get("recommended_claim_decisions", [])
        if not claim_recs:
            st.info("No claim-level AI recommendations available.")
        else:
            for rec in claim_recs:
                with st.expander(f"Claim {rec['claim_id']} — {rec.get('employee_name', 'N/A')}"):
                    st.write(f"**Amount:** ₹{rec['amount']:,.2f}")
                    st.write(f"**Category:** {rec['category']}")
                    st.write(f"**AI Suggested Decision:** {rec['ai_decision']}")
                    st.write(f"**Reason:** {rec['reason']}")


    # # Ensure app runs in Streamlit
    # if __name__ == "__main__":
    #     main()
