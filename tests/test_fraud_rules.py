from datetime import datetime, timezone
from uuid import uuid4

from src.common.fraud_rules import assess
from src.common.models import TransactionEvent


def event(**overrides):
    payload = {
        "event_id": uuid4(), "transaction_id": uuid4(), "account_id": "ACC-000001",
        "merchant_id": "travel", "transaction_type": "card", "amount": "100.00",
        "currency": "GBP", "country": "GB", "device_id": "DEV-1",
        "ip_address": "81.2.69.142", "event_time": datetime(2026, 8, 11, 12, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return TransactionEvent.model_validate(payload)


def test_normal_transaction_is_low_risk():
    result = assess(event())
    assert result.is_fraud is False
    assert result.risk_score == 0


def test_high_amount_and_country_trigger_fraud():
    result = assess(event(amount="6000.00", country="IR"))
    assert result.is_fraud is True
    assert result.risk_score == 80
    assert {"high_amount", "high_risk_country"} <= set(result.rules_triggered)


def test_velocity_rule_increases_risk():
    result = assess(event(amount="2500.00"), recent_count=5)
    assert result.is_fraud is True
    assert "velocity_threshold" in result.rules_triggered

