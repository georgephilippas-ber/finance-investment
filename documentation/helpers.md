# Helpers

`helpers/__init__.py` — small utilities shared across packages.

## `latest_weekday`
```python
def latest_weekday() -> date
```
Today on Monday to Friday, otherwise the Friday before. Used as the default valuation date by the
[bond scanner](scanners.md), so calculations run on a weekend line up with Friday's closing prices.

Public holidays are not skipped: on a holiday it returns that day, even though the latest price is from the previous
trading day.
