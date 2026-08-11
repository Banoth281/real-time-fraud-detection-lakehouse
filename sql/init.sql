CREATE TABLE IF NOT EXISTS transactions (
  event_id UUID PRIMARY KEY,
  transaction_id UUID UNIQUE NOT NULL,
  account_id TEXT NOT NULL,
  merchant_id TEXT NOT NULL,
  transaction_type TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  country CHAR(2) NOT NULL,
  device_id TEXT NOT NULL,
  event_time TIMESTAMPTZ NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_fraud BOOLEAN NOT NULL,
  risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
  rules_triggered JSONB NOT NULL,
  processing_latency_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_event_time ON transactions(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_fraud ON transactions(is_fraud, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id, event_time DESC);

CREATE OR REPLACE VIEW gold_hourly_fraud_metrics AS
SELECT date_trunc('hour', event_time) AS hour,
       COUNT(*) AS transactions,
       COUNT(*) FILTER (WHERE is_fraud) AS fraud_transactions,
       ROUND(SUM(amount), 2) AS total_value,
       ROUND(SUM(amount) FILTER (WHERE is_fraud), 2) AS fraud_value,
       ROUND(AVG(risk_score), 2) AS average_risk_score
FROM transactions
GROUP BY 1;

