# Exchanges

`clients/common/exchanges.py` — EODHD's exchanges database augmented with IBKR exchange codes. The MIC → IBKR codes live in `domain/exchanges/ibkr_operating_mic_mapping.json`; the first code in each list is the main one.

## `get_augmented_exchanges_database`
```python
def get_augmented_exchanges_database() -> DataFrame
```
EODHD's exchanges table (`read_exchanges_database()`) with two IBKR columns added from `ibkr_operating_mic_mapping.json`:
- `ibkr_exchange` — main IBKR code for the MIC (`""` if IBKR does not cover it);
- `ibkr_other_exchanges` — tuple of further IBKR codes (e.g. `("ARCA", "AMEX")` for XNYS, `("IBIS2",)` for XETR).

This is the table both [`SecurityInformationMapping`](mappings.md) methods use. Raises `ValueError` if the JSON names a MIC missing from the table.

## `print_augmented_exchanges_database`
```python
def print_augmented_exchanges_database(exchanges: DataFrame) -> None
```
Prints the frame from `get_augmented_exchanges_database` as a boxed table sorted by country and MIC — operating MIC, EODHD code, IBKR exchange, other IBKR exchanges, country, currency, name — followed by the row count and how many MICs have an IBKR code.
