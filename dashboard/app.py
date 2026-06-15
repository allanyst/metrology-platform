from __future__ import annotations
import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import os

DB_PATH = os.environ.get(
    "METROLOGY_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "db" / "metrology.duckdb")
)

st.set_page_config(
    page_title="Metrology QC Platform",
    page_icon="🔬",
    layout="wide",
)

def query(sql: str, params: list | None = None) -> pd.DataFrame:
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        return conn.execute(sql, params or []).fetchdf()
    finally:
        conn.close()

st.title("🔬 Metrology QC & Traceability Platform")
st.caption("Real-time calibration monitoring | ISO 17025 compliant")

# ── Status cards ──────────────────────────────────────────────────────────────
status_df = query("""
    SELECT cs.instrument_id, cs.instrument_name, cs.sublab,
           cs.overall_status, cs.control_zone,
           pm.risk_level, pm.days_to_failure,
           u.u_expanded_k2
    FROM gold.fact_calibration_status cs
    LEFT JOIN gold.fact_predictive_maintenance pm USING (instrument_id)
    LEFT JOIN gold.fact_uncertainty u USING (instrument_id)
    ORDER BY cs.instrument_id
""")

STATUS_COLOR = {"OK": "🟢", "WARNING": "🟡", "OUT_OF_TOLERANCE": "🔴", "CRITICAL": "🔴"}
RISK_COLOR   = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}

st.subheader("Instrument Status Overview")
cols = st.columns(4)
for i, row in status_df.iterrows():
    with cols[i % 4]:
        st.metric(
            label=f"{STATUS_COLOR.get(row['overall_status'], '⚪')} {row['instrument_id']}",
            value=row['overall_status'],
            delta=f"Risk: {row['risk_level']} | {int(row['days_to_failure']) if pd.notna(row['days_to_failure']) else '∞'} days",
        )

st.divider()

# ── Instrument selector ───────────────────────────────────────────────────────
st.subheader("Control Chart — Levey-Jennings")
col1, col2 = st.columns([2, 1])
with col1:
    selected = st.selectbox("Select instrument", status_df["instrument_id"].tolist())
with col2:
    days = st.slider("Days to show", 30, 365, 90)

chart_df = query("""
    SELECT measurement_date, mean_error,
           lt_mean_error, ucl_1s, lcl_1s,
           ucl_2s, lcl_2s, ucl_3s, lcl_3s,
           control_zone, we_rule1_violation
    FROM gold.fact_control_charts
    WHERE instrument_id = ?
      AND measurement_date >= (SELECT MAX(measurement_date) FROM gold.fact_control_charts
                               WHERE instrument_id = ?) - INTERVAL (?) DAY
    ORDER BY measurement_date
""", [selected, selected, days])

fig = go.Figure()
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["ucl_3s"],
    line=dict(color="red", dash="dash", width=1), name="±3σ", showlegend=True))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["lcl_3s"],
    line=dict(color="red", dash="dash", width=1), showlegend=False))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["ucl_2s"],
    line=dict(color="orange", dash="dot", width=1), name="±2σ"))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["lcl_2s"],
    line=dict(color="orange", dash="dot", width=1), showlegend=False))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["ucl_1s"],
    line=dict(color="green", dash="dot", width=1), name="±1σ"))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["lcl_1s"],
    line=dict(color="green", dash="dot", width=1), showlegend=False))
fig.add_trace(go.Scatter(x=chart_df["measurement_date"], y=chart_df["lt_mean_error"],
    line=dict(color="blue", width=1, dash="dash"), name="Mean"))
fig.add_trace(go.Scatter(
    x=chart_df["measurement_date"], y=chart_df["mean_error"],
    mode="lines+markers",
    marker=dict(
        color=["red" if v else "steelblue" for v in chart_df["we_rule1_violation"]],
        size=5,
    ),
    line=dict(color="steelblue", width=1.5),
    name="Daily mean error",
))
fig.update_layout(
    title=f"Levey-Jennings — {selected}",
    xaxis_title="Date", yaxis_title="Error",
    height=400, hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Risk and uncertainty ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Days to Failure by Instrument")
    pm_df = query("""
        SELECT instrument_id, days_to_failure, risk_level, trend
        FROM gold.fact_predictive_maintenance
        WHERE days_to_failure IS NOT NULL
        ORDER BY days_to_failure
    """)

    color_map = {"LOW": "green", "MEDIUM": "gold", "HIGH": "orange", "CRITICAL": "red"}
    fig2 = px.bar(pm_df, x="instrument_id", y="days_to_failure",
                  color="risk_level", color_discrete_map=color_map,
                  title="Predicted Days to Tolerance Failure")
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("Expanded Uncertainty U(k=2)")
    unc_df = query("""
        SELECT instrument_id, u_type_a, u_type_b, u_combined, u_expanded_k2
        FROM gold.fact_uncertainty
        ORDER BY u_expanded_k2 DESC
    """)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name="U type A", x=unc_df["instrument_id"],
                          y=unc_df["u_type_a"], marker_color="steelblue"))
    fig3.add_trace(go.Bar(name="U type B", x=unc_df["instrument_id"],
                          y=unc_df["u_type_b"], marker_color="coral"))
    fig3.update_layout(barmode="stack", title="Uncertainty Budget (type A + B)",
                       height=350)
    st.plotly_chart(fig3, use_container_width=True)
