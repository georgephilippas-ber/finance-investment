# Documentation

A personal investment toolkit that reads an Interactive Brokers account (read-only) and links its securities to EODHD market data.

## Contents

| Page | Covers |
|---|---|
| [Interactive Brokers client](interactive_brokers.md) | Connecting, account summary with liquidation value and returns, positions, positions → `SecurityInformation`, printing. |
| [EODHD client](eodhd.md) | Exchanges database, security lookup by ticker / ISIN / exchange, latest end-of-day price. |
| [Mappings](mappings.md) | Exchanges database with IBKR codes; `SecurityInformationMapping`: converting between IBKR and EODHD, and what it relies on (ISIN, exchange mapping, currency). |
| [Domain](domain.md) | Public data structures: `Provider`, `SecurityInformation`, `EndOfDayPrice`, `AccountInformation`, `PortfolioPosition`. |

## Layout

```
clients/
  common/              shared across providers
    domain.py          Provider, SecurityInformation, EndOfDayPrice
    mappings.py        SecurityInformationMapping, augmented exchanges database
    printing.py        print_table (boxed tables used by all print functions)
  interactive_brokers/ IBKR client, configuration, account and position types
  eodhd/               EODHD client, configuration, internal symbol type
domain/exchanges/      exchanges.sqlite and the MIC mapping JSON files
cache/eodhd/           cached EODHD responses (tracked)
```

## Setup

- **IB Gateway or TWS** running with the API enabled. Defaults `127.0.0.1:4001`, client ID `1`; override with `IBKR_HOST`, `IBKR_PORT` (`4002` for paper), `IBKR_CLIENT_ID`.
- **EODHD API key** in `EODHD_API_KEY`.
- Put both in `.env` at the project root; scripts call `load_dotenv()`.

## Running

From the project root:

```bash
python3 main.py
```

Prints the account summary and the positions table. Scripts under `research/` run as modules, e.g. `python3 -m research.main`.

## Typical flow

```python
ib = await connect()
try:
    await print_full_account_information(ib)
    for security in await get_positions_as_security_information(ib):  # Provider.IBKR, with ISIN
        eodhd = SecurityInformationMapping.from_ibkr_to_eodhd(security)  # Provider.EODHD
        print(latest_price(eodhd).close)
finally:
    disconnect(ib)
```

Starting from EODHD instead: `get_security_information_by_ticker` / `_by_isin` → `SecurityInformationMapping.from_eodhd_to_ibkr` gives the IBKR contract.

## Example

[`examples/main_features.py`](examples/main_features.py) runs all of the above end to end: exchanges database with IBKR codes, EODHD lookups by ticker and ISIN, latest price, account and positions tables, IBKR → EODHD and EODHD → IBKR conversion.

```bash
python3 documentation/examples/main_features.py
```

It works from any directory and reads `.env` from the project root. It needs `EODHD_API_KEY` (about nine EODHD calls per run with two positions); if IB Gateway / TWS is not reachable, the IBKR part is skipped.
