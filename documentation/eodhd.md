# EODHD client

`clients/eodhd/client.py` — wraps the EODHD REST API. Requires `EODHD_API_KEY` (env / `.env`). Cached responses live in `cache/eodhd/`.

## `api_key`
```python
def api_key() -> str
```
Returns `EODHD_API_KEY`; raises `RuntimeError` when it is missing.

## `get_exchanges`
```python
def get_exchanges(load_from_cache: bool = True) -> List[Dict]
```
Raw EODHD exchange list.
- `load_from_cache` — read `cache/eodhd/exchanges.json` if present instead of calling the API (the API response is always written to the cache).

## `create_exchanges_database`
```python
def create_exchanges_database(load_from_cache: bool = True) -> Path
```
Builds `domain/exchanges/exchanges.sqlite` (table `exchanges`: operating MIC, name, country, currency, EODHD code) from the exchange list plus `us_operating_mic_mapping.json`. Returns the database path.

## `read_exchanges_database`
```python
def read_exchanges_database() -> DataFrame
```
Reads the `exchanges` table (read-only).

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

## `latest_candle`
```python
def latest_candle(security: SecurityInformation, *, lookback_days: int = 14) -> EODCandle
```
Most recent daily candle for an EODHD `SecurityInformation` (`ticker.exchange`).
- `lookback_days` — window searched for the latest candle; raises `LookupError` if empty.
