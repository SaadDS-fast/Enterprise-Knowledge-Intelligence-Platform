from datetime import UTC, datetime, timedelta


def retention_deadline(days: int) -> datetime:
    if days < 1:
        raise ValueError("Retention days must be positive")
    return datetime.now(UTC) + timedelta(days=days)
