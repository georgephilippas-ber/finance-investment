# EODHD client

`clients/eodhd/client.py` — wraps the EODHD REST API. Requires `EODHD_API_KEY` (env / `.env`). Cached responses live in `cache/eodhd/`.

## `read_exchanges_database`
```python
def read_exchanges_database() -> DataFrame
```
Reads the `exchanges` table of `domain/exchanges/exchanges.sqlite` (read-only): operating MIC, name, country, currency, EODHD code. The database is built by the private `_create_exchanges_database` from the EODHD exchange list and `us_operating_mic_mapping.json`.

## `get_symbols_by_ticker`
```python
def get_symbols_by_ticker(ticker: str, *, operating_mic: Optional[str] = None, eodhd_code: Optional[str] = None) -> List[Symbol]
```
Symbols matching a ticker on one exchange.
- `ticker` — e.g. `"MSFT"` (a `TICKER.CODE` form is accepted).
- `operating_mic` / `eodhd_code` — the exchange; at least one is required, and they must agree if both are given.

## `get_symbols_by_isin`
```python
def get_symbols_by_isin(isin: str, *, currency: str) -> List[Symbol]
```
All listings of an ISIN in the given currency (one per exchange). Raises `LookupError` if the 500-result search limit is hit.

## `get_symbols_in_exchange`
```python
def get_symbols_in_exchange(exchange: str, load_from_cache: bool = True) -> List[Symbol]
```
Every symbol listed on an exchange.
- `exchange` — operating MIC or EODHD code.
- `load_from_cache` — use `cache/eodhd/symbols_<CODE>.json` when present.

## `latest_price`
```python
def latest_price(security: SecurityInformation, *, lookback_days: int = 14) -> EndOfDayPrice
```
Most recent end-of-day price for a `Provider.EODHD` `SecurityInformation` (`symbol.exchange`); raises `ValueError` for another provider.
- `lookback_days` — window searched for the latest price; raises `LookupError` if empty.
