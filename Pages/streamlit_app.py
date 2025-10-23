import streamlit as st
import pandas as pd
import plotly.express as px

# ---------- Page Config ----------
st.set_page_config(page_title="Claims Dashboard", layout="wide")

st.title("📊 Claims Processing Dashboard")

# ---------- File Upload ----------
uploaded_file = st.file_uploader("📂 Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    df_expense = pd.read_excel(uploaded_file,sheet_name="expense_claims")
    df = pd.read_excel(uploaded_file,sheet_name="dashboard_metrics")

    # Clean column names (remove spaces or special chars)
    df.columns = [c.strip().replace(" ", "_").lower() for c in df.columns]

    
    # ---------- KPIs ----------
    latest = df.iloc[-1]  # use latest record

    st.subheader("📌 Key Performance Indicators")

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    col1.metric("📝 Claims Submitted", int(df.claims_submitted.sum()))
    col2.metric("✅ Auto Approved", int(df['auto_approved_count'].sum()))
    col3.metric("⏱️ Avg Processing Time (hrs)", f"{df['avg_processing_time_hours'].mean():.2f}")

    col4.metric("⚠️ Fraud Flags", int(df['fraud_flags_detected'].sum()))
    col5.metric("🕓 Pending Claims", int(df['pending_claims'].sum()))
    col6.metric("🤖 Automation Rate", f"{(df['automation_rate'].mean())*100:.1f}%")

    st.divider()

    # ---------- Visualization Section ----------
    st.subheader("📈 Visual Insights")

    # Convert automation rate to %
    df["automation_rate_percent"] = df["automation_rate"] * 100

    # --- Bar Chart: Claims Summary ---
    fig = px.bar(
        df.melt(
            id_vars="date",
            value_vars=[
                "claims_submitted",
                "auto_approved_count",
                "pending_claims",
                "fraud_flags_detected",
            ],
        ),
        x="variable",
        y="value",
        color="variable",
        text="value",
        title="Claims Summary Over Time",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # --- Line Chart: Processing Time & Automation Rate ---
    fig2 = px.line(
        df,
        x="date",
        y=["avg_processing_time_hours", "automation_rate_percent"],
        markers=True,
        title="Processing Time vs Automation Rate",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ---------- Display Data ----------
    st.subheader("📄 Raw Data Preview")
    st.dataframe(df_expense, use_container_width=True)




    st.caption("Data source: Uploaded Excel file")
else:
    st.info("👆 Please upload an Excel file to begin.")
