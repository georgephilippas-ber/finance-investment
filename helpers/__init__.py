from datetime import date, timedelta

__all__ = ["latest_weekday"]


def latest_weekday() -> date:
    # Today on Monday to Friday, otherwise the Friday before, so weekend runs line up with Friday's closing prices.
    today_ = date.today()
    return today_ - timedelta(days=max(0, today_.weekday() - 4))
