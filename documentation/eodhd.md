# EODHD client

`clients/eodhd/client.py` — EODHD REST API: exchanges, security lookup and end-of-day prices.

- API requests require `EODHD_API_KEY` in the environment. Entry-point scripts load `.env`; the client itself
  does not. Cached reads do not require an API key.
- Cached exchange lists and exchange symbol lists live in `cache/eodhd/` (tracked in git). They have no expiry;
  use `load_from_cache=False` on the relevant function to refresh them. Ticker lookup, ISIN lookup, and latest
  prices are not cached.
- HTTP requests are synchronous, with a 30-second timeout and no application-level retries. Calling these
  functions directly in an async workflow blocks its event loop for the duration of the request.
- Every security comes back as a `Provider.EODHD` [`SecurityInformation`](domain.md#securityinformation); EODHD's raw `_Symbol` records stay inside the package.

## Exchanges

### `read_exchanges_database`
```python
def read_exchanges_database() -> DataFrame
```
Reads the `exchanges` table of `domain/exchanges/exchanges.sqlite` (read-only). One row per operating MIC with `operating_mic`, `name`, `country`, `currency` and `eodhd_code`; several MICs can share one EODHD code (all US MICs → `US`).

The database is built by the private `_create_exchanges_database` from EODHD's exchange list and
`us_operating_mic_mapping.json`. Rebuilding replaces the exchange rows in a transaction. Reads use the existing
database; they do not create it or refresh the provider data automatically.

## Security lookup

```python
def get_security_information_by_ticker(ticker: str, *, operating_mic: Optional[str] = None, eodhd_code: Optional[str] = None) -> List[SecurityInformation]
```
```python
def get_security_information_by_isin(isin: str, *, currency: str) -> List[SecurityInformation]
```
```python
def get_security_information_in_exchange(exchange: str, load_from_cache: bool = True) -> List[SecurityInformation]
```

| Function | Finds | Parameters |
|---|---|---|
| `get_security_information_by_ticker` | a ticker on one exchange | `ticker` (e.g. `"MSFT"` or `"MSFT.US"`); the exchange as `operating_mic` and/or `eodhd_code` — at least one, and they must agree |
| `get_security_information_by_isin` | every listing of an ISIN in one currency | `isin`; `currency` |
| `get_security_information_in_exchange` | every security listed on an exchange | `exchange` as operating MIC or EODHD code; `load_from_cache` — reuse `cache/eodhd/symbols_<CODE>.json` instead of calling the API |

**How results are built.** Each EODHD record becomes a `SecurityInformation` with `symbol` = EODHD ticker, `exchange` = EODHD exchange code, plus `currency` and `isin` (empty → `None`); `contract_id` is always `None`.

**Exchange normalisation.** `exchange` must be a code from the exchanges database:
- US records from the ticker and exchange lookups carry the venue (`NASDAQ`, `NYSE`, …); those with country USA become `US`.
- Records on exchanges outside the database (e.g. `IL`, LSE's international segment) are **skipped**, so a lookup can return fewer listings than EODHD has.

**Cost.** One EODHD API call per lookup (none for `get_security_information_in_exchange` when cached).

**Errors.** `ValueError` for missing parameters or a disagreeing `operating_mic` / `eodhd_code`; `LookupError` for an unknown exchange or when the ISIN search hits EODHD's 500-result limit.

## Prices

### `get_latest_price`
```python
def get_latest_price(security: SecurityInformation, *, lookback_days: int = 14) -> EndOfDayPrice
```
Most recent daily bar ([`EndOfDayPrice`](domain.md#endofdayprice)) for `symbol.exchange`, e.g. `SAP.XETRA`.
- `security` — must be `Provider.EODHD` (convert IBKR information with [`SecurityInformationMapping.from_ibkr_to_eodhd`](mappings.md)); otherwise `ValueError`.
- `lookback_days` — calendar days searched back from today, covering weekends and holidays; `LookupError` if no bar falls in the window.

One EODHD API call. The client selects the returned record with the greatest date; it does not require that
record to be from the latest trading session. Check the returned `date` when freshness matters.
