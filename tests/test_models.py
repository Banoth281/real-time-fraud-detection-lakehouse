import pytest
from pydantic import ValidationError

from src.producer.main import create_event
from src.common.models import TransactionEvent


def test_generated_event_matches_schema():
    TransactionEvent.model_validate(create_event())


def test_negative_amount_is_rejected():
    payload = create_event()
    payload["amount"] = -1
    with pytest.raises(ValidationError):
        TransactionEvent.model_validate(payload)

