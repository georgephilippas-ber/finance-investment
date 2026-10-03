# finance-investment

A personal investment toolkit that reads an Interactive Brokers account (read-only), links its securities to EODHD
market data, and tracks when positions were opened to compute annualized returns.

## Documentation

| Page                                                               | Covers                                                                                                                    |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [Interactive Brokers client](documentation/interactive_brokers.md) | Connecting, account summary with liquidation value and returns, positions with open dates and annual return, printing.   |
| [Position tracker](documentation/position_tracker.md)              | `PositionTracker`: recording open dates and lot sizes per contract in an encrypted-ID SQLite table.                      |
| [EODHD client](documentation/eodhd.md)                             | Exchanges database, security lookup by ticker / ISIN / exchange, latest end-of-day price.                                 |
| [Exchanges](documentation/exchanges.md)                            | Exchanges database with IBKR codes: get and print.                                                                        |
| [Mappings](documentation/mappings.md)                              | `SecurityInformationMapping`: converting between IBKR and EODHD, and what it relies on (ISIN, exchange mapping, currency). |
| [Domain](documentation/domain.md)                                  | Public data structures: `Provider`, `SecurityInformation`, `EndOfDayPrice`, `AccountInformation`, `PortfolioPosition`, `Lot`. |
| [Printing](documentation/printing.md)                              | `print_table`, `print_section`, `print_subsection`.                                                                       |

## Layout

```
clients/
  common/                 shared across providers
    domain.py             Provider, SecurityInformation, EndOfDayPrice
    exchanges.py          exchanges database with IBKR codes (get / print)
    mappings.py           SecurityInformationMapping
  interactive_brokers/
    client.py             account, positions, printing
    configuration.py      connection settings and tracker key (from the environment)
    domain.py             account and position types
    position_tracker.py   PositionTracker, Lot
  eodhd/                  EODHD client, configuration, internal symbol type
printing/                 print_table, print_section, print_subsection
domain/
  exchanges/              exchanges.sqlite and the MIC mapping JSON files
  positions/              positions.sqlite (position tracker)
cache/eodhd/              cached EODHD responses
documentation/            these pages and examples/main_features.py
main.py                   runs the example
```

## Setup

1. **Python packages:** `pip install -r requirements.txt` (includes `ib_async`, `pandas`, `python-dotenv`,
   `cryptography`, `babel`).
2. **IB Gateway or TWS** running with the API enabled. Defaults `127.0.0.1:4001`, client ID `1`; override with
   `IBKR_HOST`, `IBKR_PORT` (`4002` for paper), `IBKR_CLIENT_ID`.
3. **`.env`** at the project root (gitignored; scripts call `load_dotenv()`):
   - `EODHD_API_KEY` — EODHD API key.
   - `IBKR_POSITION_TRACKER_KEY` — key encrypting contract IDs in the position tracker. Generate one with
     `python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(64)).decode())"` and **back it up**:
     without it the stored contract IDs cannot be recovered.
4. **Position tracker:** `PositionTracker.create_database()` once, then `PositionTracker.add(...)` per purchase.

> [!WARNING]
> **Single-currency accounts only.** There is no FX conversion yet. If any position is in a currency other than the
> account's base currency (e.g. a USD stock in a EUR account):
> - `get_account_information` — and therefore `print_full_account_information` — raises `ValueError`, because the
>   liquidation simulation refuses to add up proceeds in different currencies;
> - the account's `total_cost`, `gross_return` and `net_return` cannot be computed.
>
> `get_positions` and `print_positions` are unaffected: they report each position in its own currency. IBKR's own
> account figures (net liquidation, cash, PnL) are already in the base currency.

## Privacy

`domain/positions/positions.sqlite` is tracked in git. Its contract IDs are encrypted, but open dates and quantities are
stored in plain text. Keep `.env` (and the key) out of git, and do not hard-code real contract IDs in committed source.

## Running

From the project root:

```bash
python3 main.py
```

runs `features()` from the [example](#example). Scripts under `research/` run as modules from the project root, e.g.
`python3 -m research.main`.

## Typical flow

```python
load_dotenv()
ib = await connect()
try:
    await print_full_account_information(ib)                            # account summary, then positions table
    for security in await get_positions_as_security_information(ib):    # Provider.IBKR, with ISIN
        eodhd = SecurityInformationMapping.from_ibkr_to_eodhd(security)  # Provider.EODHD
        print(get_latest_price(eodhd).close)
finally:
    disconnect(ib)
```

Starting from EODHD instead: `get_security_information_by_ticker` / `_by_isin` →
`SecurityInformationMapping.from_eodhd_to_ibkr` gives the IBKR contract.

## Example

[`documentation/examples/main_features.py`](documentation/examples/main_features.py) runs everything end to end:
exchanges database with IBKR codes, EODHD lookups by ticker and ISIN, latest price, IBKR → EODHD and EODHD → IBKR
conversion, and finally the account summary and positions table.

```bash
python3 documentation/examples/main_features.py
```

It works from any directory and reads `.env` from the project root. It needs `EODHD_API_KEY` (about nine EODHD calls per
run with two positions); if IB Gateway / TWS is not reachable, the IBKR part is skipped.
