import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from confluent_kafka import Producer

from src.common.config import settings

COUNTRIES = ["GB", "GB", "GB", "FR", "DE", "US", "IR"]
MERCHANTS = ["groceries", "electronics", "travel", "gaming", "fuel", "fashion"]


def create_event() -> dict:
    suspicious = random.random() < 0.07
    amount = round(random.uniform(5, 750), 2)
    country = random.choice(COUNTRIES)
    if suspicious:
        amount = round(random.uniform(4_500, 12_000), 2)
    event_time = datetime.now(timezone.utc)
    if random.random() < 0.02:
        event_time -= timedelta(minutes=random.randint(10, 60))
    return {
        "event_id": str(uuid4()),
        "transaction_id": str(uuid4()),
        "account_id": f"ACC-{random.randint(0, 999999):06d}",
        "merchant_id": random.choice(MERCHANTS),
        "transaction_type": random.choice(["card", "transfer", "cash"]),
        "amount": amount,
        "currency": "GBP",
        "country": country,
        "device_id": f"DEV-{random.randint(1, 5000):05d}",
        "ip_address": f"{random.randint(11, 220)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "event_time": event_time.isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    producer = Producer({"bootstrap.servers": settings.kafka, "client.id": "fraud-producer", "enable.idempotence": True})
    interval = float(os.getenv("PRODUCER_INTERVAL_SECONDS", "0.20"))
    while True:
        event = create_event()
        producer.produce(settings.topic, key=event["account_id"], value=json.dumps(event))
        producer.poll(0)
        print(f"published {event['transaction_id']} amount={event['amount']}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
