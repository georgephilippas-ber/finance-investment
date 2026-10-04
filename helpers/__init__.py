from calendar import FRIDAY, monthrange
from datetime import date, timedelta

from settings import MONTHS_PER_YEAR

__all__ = ["add_months", "latest_weekday"]


def add_months(day: date, months: int) -> date:
    month_index_ = day.month - 1 + months
    year_, month_ = day.year + month_index_ // MONTHS_PER_YEAR, month_index_ % MONTHS_PER_YEAR + 1
    return date(year_, month_, min(day.day, monthrange(year_, month_)[1]))


def latest_weekday() -> date:
    today_ = date.today()
    return today_ - timedelta(days=max(0, today_.weekday() - FRIDAY))
