import io
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import boto3
import psycopg
from botocore.client import Config
from confluent_kafka import Consumer, Producer
from pydantic import ValidationError

from src.common.config import settings
from src.common.fraud_rules import assess
from src.common.models import TransactionEvent


def minio_client():
    return boto3.client(
        "s3", endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"), region_name="us-east-1",
    )


def archive_bronze(client, raw: bytes, event_id: str, event_time: datetime) -> None:
    key = f"bronze/year={event_time:%Y}/month={event_time:%m}/day={event_time:%d}/{event_id}.json"
    client.put_object(Bucket=settings.minio_bucket, Key=key, Body=io.BytesIO(raw), ContentType="application/json")


def main() -> None:
    consumer = Consumer({
        "bootstrap.servers": settings.kafka, "group.id": "fraud-processor-v1",
        "auto.offset.reset": "earliest", "enable.auto.commit": False,
    })
    dlq = Producer({"bootstrap.servers": settings.kafka, "client.id": "fraud-dlq-producer"})
    s3 = minio_client()
    windows: dict[str, deque[datetime]] = defaultdict(deque)
    consumer.subscribe([settings.topic])

    with psycopg.connect(settings.database_url, autocommit=False) as conn:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                print(message.error())
                continue
            started = time.perf_counter()
            raw = message.value()
            try:
                event = TransactionEvent.model_validate_json(raw)
                now = datetime.now(timezone.utc)
                window = windows[event.account_id]
                cutoff = now - timedelta(minutes=5)
                while window and window[0] < cutoff:
                    window.popleft()
                result = assess(event, len(window))
                window.append(now)
                archive_bronze(s3, raw, str(event.event_id), event.event_time)
                latency = int((time.perf_counter() - started) * 1000)
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO transactions
                        (event_id,transaction_id,account_id,merchant_id,transaction_type,amount,currency,country,device_id,event_time,is_fraud,risk_score,rules_triggered,processing_latency_ms)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                        ON CONFLICT (event_id) DO NOTHING""",
                        (event.event_id,event.transaction_id,event.account_id,event.merchant_id,event.transaction_type.value,event.amount,event.currency,event.country,event.device_id,event.event_time,result.is_fraud,result.risk_score,json.dumps(result.rules_triggered),latency),
                    )
                conn.commit()
                consumer.commit(message=message, asynchronous=False)
                print(f"processed {event.transaction_id} risk={result.risk_score} fraud={result.is_fraud}")
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                conn.rollback()
                envelope = {"error": str(exc), "raw": raw.decode("utf-8", errors="replace"), "failed_at": datetime.now(timezone.utc).isoformat()}
                dlq.produce(settings.dlq_topic, value=json.dumps(envelope))
                dlq.flush()
                consumer.commit(message=message, asynchronous=False)


if __name__ == "__main__":
    main()

