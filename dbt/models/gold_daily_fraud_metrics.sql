select
  date(event_time) as transaction_date,
  count(*) as transactions,
  count(*) filter (where is_fraud) as fraud_transactions,
  round(sum(amount), 2) as total_value,
  round(sum(amount) filter (where is_fraud), 2) as fraud_value,
  round(avg(risk_score), 2) as average_risk_score,
  round(avg(processing_latency_ms), 2) as average_latency_ms
from public.transactions
group by 1

