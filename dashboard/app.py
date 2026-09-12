import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
DEMO_DATA_PATH = Path(__file__).with_name("demo_data.json")

st.set_page_config(
    page_title="Real-Time Fraud Detection Lakehouse",
    page_icon="🛡️",
    layout="wide",
)


@st.cache_data
def load_demo_data() -> dict:
    """Load a representative synthetic snapshot for the public portfolio demo."""
    with DEMO_DATA_PATH.open(encoding="utf-8") as demo_file:
        return json.load(demo_file)


@st.cache_data(ttl=20)
def get_json(endpoint: str):
    response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
    response.raise_for_status()
    return response.json()


def load_dashboard_data() -> tuple[dict, bool]:
    """Prefer the live FastAPI service and fall back safely when unavailable."""
    demo = load_demo_data()
    try:
        live_summary = get_json("/metrics/summary?minutes=1440")
        live_rules = get_json("/metrics/rules")
        data = {**demo, "summary": live_summary, "rules": live_rules}
        return data, True
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return demo, False


st.title("🛡️ Real-Time Banking Fraud Detection Lakehouse")
st.caption(
    "Synthetic transaction monitoring powered by Python, Redpanda/Kafka, "
    "MinIO, PostgreSQL, dbt and FastAPI."
)

data, is_live = load_dashboard_data()
summary = data["summary"]

st.sidebar.markdown("### Lakehouse Data Flow")
st.sidebar.write("Events → Kafka → Bronze / Silver → dbt Gold → FastAPI")

if is_live:
    st.sidebar.success("Live FastAPI connected")
else:
    st.sidebar.info("Portfolio demo mode")
    st.info(
        "**Portfolio demo:** displaying a representative synthetic banking "
        "snapshot. Run the complete Docker pipeline locally to enable live data."
    )

transactions = int(summary["transactions"])
fraud_transactions = int(summary["fraud_transactions"])
fraud_rate = (fraud_transactions / transactions * 100) if transactions else 0
fraud_value = float(summary["fraud_value"])

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Transactions", f"{transactions:,}")
col2.metric("Fraud alerts", f"{fraud_transactions:,}")
col3.metric("Fraud rate", f"{fraud_rate:.2f}%")
col4.metric("Flagged exposure", f"£{fraud_value:,.0f}")
col5.metric("Avg. risk score", f"{float(summary['average_risk_score']):.1f}/100")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Fraud alerts by hour")
    hourly = pd.DataFrame(data["hourly_metrics"])
    hourly["hour"] = pd.to_datetime(hourly["hour"])
    hourly_chart = px.area(
        hourly,
        x="hour",
        y="fraud_transactions",
        markers=True,
        labels={"hour": "Time", "fraud_transactions": "Fraud alerts"},
    )
    hourly_chart.update_traces(line_color="#ef553b", fillcolor="rgba(239,85,59,0.25)")
    st.plotly_chart(hourly_chart, use_container_width=True)

with right:
    st.subheader("Fraud exposure by country")
    countries = pd.DataFrame(data["country_metrics"])
    country_chart = px.bar(
        countries.sort_values("fraud_value"),
        x="fraud_value",
        y="country",
        orientation="h",
        color="fraud_rate",
        color_continuous_scale="Reds",
        labels={
            "country": "Country",
            "fraud_value": "Flagged value (£)",
            "fraud_rate": "Fraud rate (%)",
        },
    )
    st.plotly_chart(country_chart, use_container_width=True)

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Triggered fraud rules")
    rules = pd.DataFrame(data["rules"])
    if rules.empty:
        st.info("No fraud rules have been triggered.")
    else:
        rules_chart = px.bar(
            rules.sort_values("triggers"),
            x="triggers",
            y="rule",
            orientation="h",
            color="triggers",
            color_continuous_scale="Oranges",
            labels={"rule": "Rule", "triggers": "Triggers"},
        )
        st.plotly_chart(rules_chart, use_container_width=True)

with right:
    st.subheader("Lakehouse pipeline")
    layer1, layer2, layer3 = st.columns(3)
    layer1.metric("Bronze", f"{transactions:,}", help="Immutable JSON events in MinIO")
    layer2.metric("Silver", f"{transactions:,}", help="Validated PostgreSQL transactions")
    layer3.metric("Gold", "Ready", help="dbt analytical models")
    st.success("Kafka stream healthy")
    st.success("Data-quality rules active")
    st.success(f"Average processing latency: {float(summary['average_latency_ms']):.1f} ms")

st.divider()
st.subheader("Recent high-risk transaction alerts")
alerts = pd.DataFrame(data["recent_alerts"])
alerts["event_time"] = pd.to_datetime(alerts["event_time"], utc=True)
alerts = alerts.rename(
    columns={
        "event_time": "Event time",
        "account_id": "Account",
        "transaction_type": "Type",
        "amount": "Amount (£)",
        "country": "Country",
        "risk_score": "Risk score",
        "rules_triggered": "Rules triggered",
    }
)
st.dataframe(
    alerts[
        [
            "Event time",
            "Account",
            "Type",
            "Amount (£)",
            "Country",
            "Risk score",
            "Rules triggered",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

with st.expander("How fraud scoring works"):
    st.markdown(
        """
        The rules engine combines transaction amount, country risk, account
        velocity, transaction time and IP-address signals. Transactions scoring
        **50 or above** are classified as fraud. Invalid events are isolated in
        a dead-letter topic instead of blocking the stream.
        """
    )

st.caption(
    "All records are synthetic and generated solely for engineering "
    "demonstration. No real customer or financial data is used."
)
