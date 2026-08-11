from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TransactionType(StrEnum):
    CARD = "card"
    TRANSFER = "transfer"
    CASH = "cash"


class TransactionEvent(BaseModel):
    event_id: UUID
    transaction_id: UUID
    account_id: str = Field(pattern=r"^ACC-[0-9]{6}$")
    merchant_id: str
    transaction_type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    country: str = Field(pattern=r"^[A-Z]{2}$")
    device_id: str
    ip_address: str
    event_time: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("event_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        return value


class FraudAssessment(BaseModel):
    is_fraud: bool
    risk_score: int = Field(ge=0, le=100)
    rules_triggered: list[str]

