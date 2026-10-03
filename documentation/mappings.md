# Mappings

`clients/common/mappings.py` — converts [`SecurityInformation`](domain.md#securityinformation) between IBKR and EODHD identifiers.

## `SecurityInformationMapping`

```python
class SecurityInformationMapping:
    @staticmethod
    def from_ibkr_to_eodhd(security: SecurityInformation) -> SecurityInformation

    @staticmethod
    async def from_eodhd_to_ibkr(ib: IB, security: SecurityInformation, *, timeout: float = 50) -> SecurityInformation
```

| Method | Input | Output | Needs |
|---|---|---|---|
| `from_ibkr_to_eodhd` | `Provider.IBKR` | `Provider.EODHD` | one EODHD API call; synchronous |
| `from_eodhd_to_ibkr` | `Provider.EODHD` | `Provider.IBKR` (with `contract_id`) | a connected `IB` session, one IBKR request (`timeout` seconds); asynchronous |

`isin` and `currency` are carried over unchanged; `symbol` and `exchange` are replaced by the target provider's.

### What they rely on

1. **The ISIN — which security.** It is the only key used to find the security at the target provider; the source `symbol` is never used. Differing tickers therefore convert correctly (IBKR `BP.` ↔ EODHD `BP`). Without an ISIN both methods raise `ValueError`.
2. **The exchange mapping — which listing.** An ISIN usually trades on many venues (SAP: Xetra, Frankfurt, Stuttgart, London, …); the exchange picks one. Exchanges are translated by joining EODHD's exchanges table (`read_exchanges_database()`) with `domain/exchanges/ibkr_operating_mic_mapping.json` on the operating MIC — see [`get_augmented_exchanges_database`](exchanges.md), which adds:
   - `ibkr_exchange` — main IBKR code (`""` if IBKR does not cover the MIC);
   - `ibkr_other_exchanges` — further codes, e.g. `("ARCA", "AMEX")` for XNYS, `("IBIS2",)` for XETR.

   It raises `ValueError` if the JSON names a MIC missing from the table.
3. **The currency — which line of that listing.** Only listings in the same currency are kept (a security can trade in several currencies on one venue).
4. **The target provider's data.** `get_security_information_by_isin` for EODHD; IBKR contract details by ISIN for IBKR.

### `from_ibkr_to_eodhd` — step by step

1. Rejects input that is not `Provider.IBKR` or has no ISIN (`ValueError`).
2. Finds the exchanges whose `ibkr_exchange` or `ibkr_other_exchanges` contains `security.exchange` (e.g. `IBIS` → XETR) and requires exactly one EODHD code among them (`XETRA`); otherwise `LookupError`.
3. Calls `get_security_information_by_isin(isin, currency=currency)` and keeps the listings on that EODHD exchange.
4. Requires exactly one EODHD ticker (`LookupError` otherwise) and returns it as `symbol`, with the EODHD code as `exchange` and `contract_id = None`.

### `from_eodhd_to_ibkr` — step by step

1. Rejects input that is not `Provider.EODHD` or has no ISIN (`ValueError`).
2. Collects every IBKR code (main and other) of all MICs with that EODHD code. One EODHD code can span several MICs: `US` → XNAS, XNYS, XCBO, OTCM → `NASDAQ`, `NYSE`, `ARCA`, `AMEX`, `BATS`, `PINK`. None → `LookupError`.
3. Requests IBKR contract details for the ISIN (`secType="STK"`, `secIdType="ISIN"`), which returns every listing and routing venue.
4. Keeps contracts in the same currency whose **primary exchange** is one of the collected codes, de-duplicated by contract ID, and requires exactly one (`LookupError` otherwise).
5. Returns IBKR's `symbol`, the primary exchange as `exchange`, and the `contract_id`.

### Behaviour and limits

- **Round trip.** IBKR → EODHD → IBKR returns an identical object for primary listings (verified for SAP and Volkswagen `VOW3` on Xetra / IBIS; AAPL from EODHD resolves to NASDAQ, contract 265598).
- **Primary listings only towards IBKR.** IBKR is matched on the primary exchange, so an EODHD listing on a secondary venue (e.g. `F` Frankfurt for a German stock whose primary is Xetra) finds no match.
- **Mapping coverage.** Exchanges without IBKR codes in the JSON (e.g. TSX Venture, Hamburg) cannot be converted in either direction.
- **ISIN quality.** EODHD records occasionally lack an ISIN, and a security whose ISIN changed (e.g. after a merger) matches only under the current one.
- **Stocks and ETFs only** towards IBKR (`secType="STK"`).
