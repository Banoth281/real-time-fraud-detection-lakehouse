from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import FastAPI, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from src.common.config import settings

app = FastAPI(title="Real-Time Fraud Lakehouse API", version="1.0.0")
REQUESTS = Counter("fraud_api_requests_total", "API requests", ["endpoint"])


def fetch_one(query: str, params=()):
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(query, params)
        columns = [d.name for d in cur.description]
        return dict(zip(columns, cur.fetchone()))


@app.get("/health")
def health():
    REQUESTS.labels("health").inc()
    row = fetch_one("SELECT 1 AS database")
    return {"status": "ok", **row}


@app.get("/metrics/summary")
def summary(minutes: int = Query(60, ge=1, le=1440)):
    REQUESTS.labels("summary").inc()
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return fetch_one(
        """SELECT COUNT(*) AS transactions,
        COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
        COALESCE(ROUND(SUM(amount),2),0) AS total_value,
        COALESCE(ROUND(SUM(amount) FILTER (WHERE is_fraud),2),0) AS fraud_value,
        COALESCE(ROUND(AVG(risk_score),2),0) AS average_risk_score,
        COALESCE(ROUND(AVG(processing_latency_ms),2),0) AS average_latency_ms
        FROM transactions WHERE event_time >= %s""", (since,)
    )


@app.get("/metrics/rules")
def rules():
    REQUESTS.labels("rules").inc()
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute("""SELECT rule, COUNT(*) AS triggers FROM transactions,
                    jsonb_array_elements_text(rules_triggered) AS rule
                    GROUP BY rule ORDER BY triggers DESC""")
        return [{"rule": row[0], "triggers": row[1]} for row in cur.fetchall()]


@app.get("/prometheus")
def prometheus():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

