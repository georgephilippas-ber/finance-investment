# Helpers

`helpers/__init__.py` — small utilities shared across packages.

## `add_months`
```python
def add_months(day: date, months: int) -> date
```
`day` moved by `months` (negative to go back). The day of the month is kept where it exists and otherwise clamped to
the month's last day: 31 January + 1 month is 28 (or 29) February. Used for bond coupon dates and for maturity-date
filters in `research/main.py`.

## `latest_weekday`
```python
def latest_weekday() -> date
```
Today on Monday to Friday, otherwise the Friday before. Used as the default valuation date by the
[bond scanner](scanners.md), so calculations run on a weekend line up with Friday's closing prices.

Public holidays are not skipped: on a holiday it returns that day, even though the latest price is from the previous
trading day.
