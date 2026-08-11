from datetime import datetime, timezone
from ipaddress import ip_address

from .models import FraudAssessment, TransactionEvent

HIGH_RISK_COUNTRIES = {"KP", "IR", "SY"}


def assess(event: TransactionEvent, recent_count: int = 0) -> FraudAssessment:
    score = 0
    rules: list[str] = []
    amount = float(event.amount)

    if amount >= 5_000:
        score += 45
        rules.append("high_amount")
    elif amount >= 2_000:
        score += 25
        rules.append("elevated_amount")

    if event.country in HIGH_RISK_COUNTRIES:
        score += 35
        rules.append("high_risk_country")

    if recent_count >= 5:
        score += 30
        rules.append("velocity_threshold")

    hour = event.event_time.astimezone(timezone.utc).hour
    if hour < 5:
        score += 10
        rules.append("unusual_hour")

    try:
        if ip_address(event.ip_address).is_private:
            score += 10
            rules.append("private_ip")
    except ValueError:
        score += 25
        rules.append("invalid_ip")

    score = min(score, 100)
    return FraudAssessment(is_fraud=score >= 50, risk_score=score, rules_triggered=rules)

