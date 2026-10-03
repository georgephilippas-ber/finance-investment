# Mappings

`clients/common/mappings.py` — links EODHD and IBKR identifiers. The MIC → IBKR exchange codes live in `domain/exchanges/ibkr_operating_mic_mapping.json` (first code in each list is the main one).

## Security conversion (IBKR ↔ EODHD)

```python
def ibkr_to_eodhd_security_information(security: SecurityInformation) -> SecurityInformation
```
```python
async def eodhd_to_ibkr_security_information(ib: IB, security: SecurityInformation, *, timeout: float = 50) -> SecurityInformation
```

Convert a `SecurityInformation` from one provider's identifiers to the other's. `ibkr_to_eodhd_security_information` takes `Provider.IBKR` and returns `Provider.EODHD`; `eodhd_to_ibkr_security_information` does the reverse. `isin` and `currency` are carried over unchanged.

### What they rely on

1. **The ISIN — the identity of the security.** It is the only key used to find the security at the target provider. The source `symbol` is never used for the lookup, so differing tickers convert correctly (IBKR `GRE1` ↔ EODHD `GRE`, IBKR `BP.` ↔ EODHD `BP`). Without an ISIN both functions raise `ValueError`.
2. **The exchange mapping — which listing.** An ISIN usually trades on many venues (EXV1 is on Xetra, Frankfurt, Munich, Stuttgart, …). The exchange decides which of those listings is returned. It is translated through EODHD's exchanges table (`read_exchanges_database()`) joined with `ibkr_operating_mic_mapping.json` on the operating MIC by the private `_augmented_exchanges_database_ibkr`, which adds two columns: `ibkr_exchange` (main IBKR code, `""` when IBKR does not cover the MIC) and `ibkr_other_exchanges` (further codes, e.g. `("ARCA", "AMEX")` for XNYS, `("IBIS2",)` for XETR). It raises `ValueError` if the JSON names a MIC missing from the table.
3. **The currency — which line of that listing.** Only listings in the same currency are kept (a security can trade in EUR and USD on the same venue).
4. **The target provider's data.** EODHD's ISIN search for one direction, IBKR's contract details for the other.

### `ibkr_to_eodhd_security_information` — step by step

1. Rejects input that is not `Provider.IBKR` or has no ISIN (`ValueError`).
2. Finds the rows of the exchanges table whose `ibkr_exchange` or `ibkr_other_exchanges` contains `security.exchange` (e.g. `IBIS` → XETR) and requires them to share exactly one EODHD code (`XETRA`); otherwise `LookupError`.
3. Calls `get_symbols_by_isin(isin, currency=currency)` — **one EODHD API call** — and keeps the results on that EODHD exchange.
4. Requires exactly one EODHD ticker among them (`LookupError` otherwise) and returns it as `symbol`, with the EODHD code as `exchange`. `contract_id` is `None`.

Synchronous; no IBKR connection needed.

### `eodhd_to_ibkr_security_information` — step by step

1. Rejects input that is not `Provider.EODHD` or has no ISIN (`ValueError`).
2. Collects every IBKR code (main and other) of all MICs with that EODHD code. One EODHD code can span several MICs: `US` → XNAS, XNYS, XCBO, OTCM → `NASDAQ`, `NYSE`, `ARCA`, `AMEX`, `BATS`, `PINK`. No codes → `LookupError`.
3. Requests IBKR contract details for the ISIN (`secType="STK"`, `secIdType="ISIN"`) — **one IBKR request**, bounded by `timeout` seconds. This returns every listing and routing venue of the security.
4. Keeps contracts in the same currency whose **primary exchange** is one of the collected codes, de-duplicated by contract ID, and requires exactly one (`LookupError` otherwise).
5. Returns IBKR's `symbol`, `primaryExchange` as `exchange`, and the `contract_id`.

Asynchronous; needs a connected `IB` session, no EODHD API call.

### Behaviour and limits

- **Round trip.** IBKR → EODHD → IBKR returns an identical object for primary listings (verified for EXV1/IBIS and GRE1/SBF).
- **Primary listings only in the IBKR direction.** IBKR is matched on the *primary* exchange, so an EODHD listing on a secondary venue (e.g. `F` Frankfurt for a German stock whose primary is Xetra) finds no match.
- **Mapping coverage.** Exchanges without IBKR codes in `ibkr_operating_mic_mapping.json` (e.g. TSX Venture, Hamburg) cannot be converted in either direction.
- **ISIN quality.** EODHD records occasionally lack an ISIN, and a security whose ISIN changed (e.g. after a merger) only matches under the current one.
- **Stocks/ETFs only** in the IBKR direction (`secType="STK"`).
