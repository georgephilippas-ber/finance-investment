# Documentation

A personal investment toolkit that reads an Interactive Brokers account (read-only) and links its securities to EODHD market data.

## Contents

| Page | Covers |
|---|---|
| [Interactive Brokers client](interactive_brokers.md) | Connecting, account summary (incl. liquidation value and returns), positions, conversion of positions to `SecurityInformation`, printing. |
| [EODHD client](eodhd.md) | Exchanges database, symbol search by ticker / ISIN / exchange, latest end-of-day price. |
| [Mappings](mappings.md) | Converting `SecurityInformation` between IBKR and EODHD, and what that relies on (ISIN, exchange mapping, currency). |
| [Domain](domain.md) | Every data structure used by the public functions: `Provider`, `SecurityInformation`, `AccountInformation`, `PortfolioPosition`, `Symbol`, `EndOfDayPrice`. |

## Setup

- **IB Gateway or TWS** running with the API enabled. Defaults: `127.0.0.1:4001`, client ID `1`; override with `IBKR_HOST`, `IBKR_PORT` (e.g. `4002` for paper), `IBKR_CLIENT_ID`.
- **EODHD API key** in `EODHD_API_KEY`.
- Both go in `.env` at the project root, loaded with `load_dotenv()`.

## Running

From the project root:

```bash
python3 main.py
```

prints the account summary and positions table. Scripts under `research/` run as modules, e.g. `python3 -m research.main`.

## Typical flow

1. `connect()` → `IB` session.
2. `get_account_information()` / `get_positions()` → `AccountInformation` / `PortfolioPosition`s (or `print_full_account_information()` to print both).
3. `positions_to_security_information()` → `Provider.IBKR` `SecurityInformation`s with ISINs.
4. `ibkr_to_eodhd_security_information()` → `Provider.EODHD` `SecurityInformation` → `latest_price()`.
5. `disconnect()`.
