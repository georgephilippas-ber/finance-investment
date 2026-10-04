from datetime import date, timedelta

__all__ = ["latest_weekday"]


def latest_weekday() -> date:
    today_ = date.today()
    return today_ - timedelta(days=max(0, today_.weekday() - 4))
