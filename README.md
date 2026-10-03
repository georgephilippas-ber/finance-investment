# finance-investment

A personal investment toolkit that reads an Interactive Brokers account (read-only) and links its securities to EODHD
market data.

## Documentation

| Page                                                               | Covers                                                                                                                     |
|--------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| [Interactive Brokers client](documentation/interactive_brokers.md) | Connecting, account summary with liquidation value and returns, positions, positions → `SecurityInformation`, printing.    |
| [EODHD client](documentation/eodhd.md)                             | Exchanges database, security lookup by ticker / ISIN / exchange, latest end-of-day price.                                  |
| [Exchanges](documentation/exchanges.md)                            | Exchanges database with IBKR codes: get and print.                                                                         |
| [Mappings](documentation/mappings.md)                              | `SecurityInformationMapping`: converting between IBKR and EODHD, and what it relies on (ISIN, exchange mapping, currency). |
| [Domain](documentation/domain.md)                                  | Public data structures: `Provider`, `SecurityInformation`, `EndOfDayPrice`, `AccountInformation`, `PortfolioPosition`.     |

## Layout

```
clients/
  common/              shared across providers
    domain.py          Provider, SecurityInformation, EndOfDayPrice
    exchanges.py       exchanges database with IBKR codes (get / print)
    mappings.py        SecurityInformationMapping
  interactive_brokers/ IBKR client, configuration, account and position types
  eodhd/               EODHD client, configuration, internal symbol type
printing/              print_table (boxed tables), print_section, print_subsection (headings)
domain/exchanges/      exchanges.sqlite and the MIC mapping JSON files
cache/eodhd/           cached EODHD responses (tracked)
```

## Setup

- **IB Gateway or TWS** running with the API enabled. Defaults `127.0.0.1:4001`, client ID `1`; override with
  `IBKR_HOST`, `IBKR_PORT` (`4002` for paper), `IBKR_CLIENT_ID`.
- **EODHD API key** in `EODHD_API_KEY`.
- Put both in `.env` at the project root; scripts call `load_dotenv()`.

> [!WARNING]
> **Single-currency accounts only.** There is no FX conversion yet. If any position is in a currency other than the
account's base currency (e.g. a USD stock in a EUR account):
> - `get_account_information` — and therefore `print_full_account_information` — raises `ValueError`, because the
    liquidation simulation refuses to add up proceeds in different currencies;
> - the account's `total_cost`, `gross_return` and `net_return` cannot be computed.
>
> `get_positions` and `print_positions` are unaffected: they report each position in its own currency. IBKR's own
account figures (net liquidation, cash, PnL) are already in the base currency.

## Running

From the project root:

```bash
python3 main.py
```

runs `features()` from the [example](#example), which shows everything working end to end. Scripts under `research/`
run as modules from the project root, e.g. `python3 -m research.main`.

## Typical flow

```python
ib = await connect()
try:
    await print_full_account_information(ib)
    for security in await get_positions_as_security_information(ib):  # Provider.IBKR, with ISIN
        eodhd = SecurityInformationMapping.from_ibkr_to_eodhd(security)  # Provider.EODHD
        print(get_latest_price(eodhd).close)
finally:
    disconnect(ib)
```

Starting from EODHD instead: `get_security_information_by_ticker` / `_by_isin` →
`SecurityInformationMapping.from_eodhd_to_ibkr` gives the IBKR contract.

## Example

[`documentation/examples/main_features.py`](documentation/examples/main_features.py) runs all of the above end to end:
exchanges database with IBKR codes, EODHD lookups by ticker and ISIN, latest price, account and positions tables, IBKR →
EODHD and EODHD → IBKR conversion.

```bash
python3 documentation/examples/main_features.py
```

It works from any directory and reads `.env` from the project root. It needs `EODHD_API_KEY` (about nine EODHD calls per
run with two positions); if IB Gateway / TWS is not reachable, the IBKR part is skipped.
