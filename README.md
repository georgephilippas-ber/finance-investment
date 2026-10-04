# finance-investment

A personal investment toolkit that reads an Interactive Brokers account (read-only by default), links its securities to EODHD
market data, records position opening dates to estimate annualized unrealized returns, and scans IBKR for bonds with
their yields.

## Documentation

| Page                                                               | Covers                                                                                                                    |
|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [Interactive Brokers client](documentation/interactive_brokers.md) | Connecting, account summary with liquidation value and returns, positions with open dates and annual return, printing.   |
| [Position tracker](documentation/position_tracker.md)              | `PositionTracker`: recording open dates and lot sizes per contract in an encrypted-ID SQLite table.                      |
| [EODHD client](documentation/eodhd.md)                             | Exchanges database, security lookup by ticker / ISIN / exchange, latest end-of-day price.                                 |
| [Exchanges](documentation/exchanges.md)                            | Exchanges database with IBKR codes: get and print.                                                                        |
| [Mappings](documentation/mappings.md)                              | `SecurityInformationMapping`: converting between IBKR and EODHD, and what it relies on (ISIN, exchange mapping, currency). |
| [Domain](documentation/domain.md)                                  | Public data structures: `Provider`, `SecurityInformation`, `EndOfDayPrice`, `AccountInformation`, `PortfolioPosition`, `Lot`, and an index of the bond types. |
| [Printing](documentation/printing.md)                              | `print_table`, `print_section`, `print_subsection`.                                                                       |
| [Bond scanner](documentation/scanner.md)                           | `interactive_brokers_scan_bonds`, `quote_bonds`, `Bond` (dirty price, yield to maturity, yield without reinvestment), `print_bond(s)`.        |
| [Helpers](documentation/helpers.md)                                | `latest_weekday`.                                                                                                         |
| [Bond scanning tutorial](research/bond-scanning-europe.md)         | IBKR scanner codes, filter tags and ready-made queries for European government and corporate bonds.                      |

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
    scanner/              bond scanning
      __init__.py         hides IBKR's harmless scanner-cancelled message
      fixed_income.py     scan_bonds, quote_bonds
      domain.py           Bond, BondQuote, BondFilters
      printing.py         print_bond, print_bonds
  eodhd/                  EODHD client, configuration, internal symbol type
printing/                 print_table, print_section, print_subsection
helpers/                  latest_weekday
domain/
  exchanges/              exchanges.sqlite and the MIC mapping JSON files
  positions/              positions.sqlite (position tracker)
cache/eodhd/              cached EODHD responses
documentation/            these pages and examples/main_features.py
main.py                   prints the IBKR account summary and positions
research/
  main.py                 prints the account summary and positions, then scans and prints EUR corporate bonds
  configuration.py        file name for a dump of IBKR's scanner parameters
  bond-scanning-europe.md bond scanning tutorial
```

## Setup

1. **Python packages:** `pip install -r requirements.txt` (includes `ib_async`, `pandas`, `python-dotenv`,
   `cryptography`, `babel`, and `numpy` and `scipy` for bond yields).
2. **IB Gateway or TWS** running with the API enabled. Defaults `127.0.0.1:4001`, client ID `1`; override with
   `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID`. Match the API socket port configured in Gateway or TWS
   (`4002` is the paper Gateway convention).
3. **Environment settings:** the entry-point scripts load a project-root `.env` (gitignored). The client functions
   themselves read environment variables; when calling them from your own script, load `.env` first if needed.
   - `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID` — optional connection overrides.
   - `EODHD_API_KEY` — required for EODHD API requests and the full example; not used by `main.py`.
   - `IBKR_POSITION_TRACKER_KEY` — key encrypting contract IDs in the position tracker. Generate one with
     `python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(64)).decode())"` and **back it up**:
     without it the stored contract IDs cannot be recovered.
4. **Position tracker (optional for the account report):** call `PositionTracker.create_database()` if the table
   does not exist, then record lots with `PositionTracker.add(...)`. There is one row per contract and date:
   another `add` on the same date replaces its quantity, so supply the day's total. Without the database, key,
   or matching lot, the report omits the opening date and annualized estimate.

## Calculation limits

- Account gross and net return describe the current open positions, not historical account performance. They do
  not incorporate a transaction history, deposits, withdrawals, or a separate dividend cash-flow series.
- Annual return is an estimate based on unrealized return and the quantity-weighted age of manually recorded
  lots. It is not a money-weighted or time-weighted return. Tracker quantities are not automatically reconciled
  with IBKR; see the [formula and missing-value rules](documentation/domain.md#portfolioposition).
- Liquidation proceeds are IBKR market value less an estimated commission from `get_commission` (EUR and USD
  stock/ETF schedules only); spread, slippage, fees and taxes are not included. Account cost sums
  signed long and short costs, which can cancel. The implementation does not reject these unsupported cases;
  restrict these estimates to long stock/ETF positions in the account's base currency.

> [!WARNING]
> **Single-currency accounts only.** There is no FX conversion yet. If any position is in a currency other than the
> account's base currency (e.g. a USD stock in a EUR account):
> - the account's liquidation value, `total_cost`, `gross_return` and `net_return` are `None` (printed `-`),
>   because amounts in different currencies are not added up.
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

`main.py` loads `.env`, connects to IBKR, prints the account summary and positions, then disconnects on success.
It does not call EODHD or run `features()`. The entry point currently has no `finally` block for disconnection on errors.

Scripts under `research/` run as modules from the project root, e.g. `python3 -m research.main`. That script
loads `.env`, prints the account summary and positions, scans IBKR for EUR investment-grade corporate bonds, prints
them with their yields, and disconnects in a `finally` block. Live bond prices need a European bond market-data
subscription; otherwise previous closes are used.

## Typical flow

Save this script in the project root and run it with Python:

```python
from asyncio import run
from pathlib import Path

from dotenv import load_dotenv

from clients.common.mappings import SecurityInformationMapping
from clients.eodhd.client import get_latest_price
from clients.interactive_brokers.client import (
    connect, disconnect, get_positions_as_security_information, print_full_account_information,
)


async def main():
    load_dotenv(Path(__file__).resolve().parent / ".env")
    ib = await connect()
    try:
        await print_full_account_information(ib)
        for security in await get_positions_as_security_information(ib):
            eodhd = SecurityInformationMapping.from_ibkr_to_eodhd(security)
            print(get_latest_price(eodhd).close)
    finally:
        disconnect(ib)


if __name__ == "__main__":
    run(main())
```

Starting from EODHD instead: `get_security_information_by_ticker` / `_by_isin` returns a list of securities;
choose a listing with an ISIN, then `await SecurityInformationMapping.from_eodhd_to_ibkr(ib, security)` to get
its IBKR `SecurityInformation`, including the contract ID.

## Example

[`documentation/examples/main_features.py`](documentation/examples/main_features.py) runs everything end to end:
exchanges database with IBKR codes, EODHD lookups by ticker and ISIN, latest price, IBKR → EODHD and EODHD → IBKR
conversion, and finally the account summary and positions table.

```bash
python3 documentation/examples/main_features.py
```

The command above is relative to the project root. The script can also be invoked by absolute path from another
directory; it reads `.env` from the project root. It needs `EODHD_API_KEY` (five EODHD requests plus two per
position when all steps succeed). If connecting to IB Gateway / TWS raises a connection, OS, or timeout error,
the IBKR part is skipped. Errors in EODHD or after a successful IBKR connection propagate.
