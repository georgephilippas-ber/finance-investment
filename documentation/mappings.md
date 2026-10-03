# Mappings

`clients/common/mappings.py` — links EODHD and IBKR identifiers. The MIC → IBKR exchange codes live in `domain/exchanges/ibkr_operating_mic_mapping.json` (first code in each list is the main one).

## `augmented_exchanges_database_ibkr`
```python
def augmented_exchanges_database_ibkr(exchanges: DataFrame) -> DataFrame
```
Returns a copy of the exchanges frame (from `read_exchanges_database()`) with two extra columns:
- `ibkr_exchange` — main IBKR code for the MIC (`""` when IBKR does not cover it).
- `ibkr_other_exchanges` — tuple of further IBKR codes (e.g. `("ARCA", "AMEX")` for XNYS, `("IBIS2",)` for XETR).

Raises `ValueError` if the JSON names a MIC that is not in the frame.

## `ibkr_to_eodhd_security_information`
```python
def ibkr_to_eodhd_security_information(security: IBKRSecurityInformation) -> EODHDSecurityInformation
```
Converts an IBKR `SecurityInformation` (ISIN required) into the EODHD one (`ticker`, `exchange`, `isin`, `currency`).
- Maps the IBKR exchange (main or other code) to exactly one EODHD exchange code.
- Takes the EODHD ticker from `get_symbols_by_isin` on that exchange (tickers can differ, e.g. IBKR `GRE1` → EODHD `GRE`).

Costs one EODHD API call; raises `LookupError` when the exchange or ticker is missing or ambiguous.
