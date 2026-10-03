# Domain

Data structures that public functions take or return. All are plain dataclasses (plus one enum); amounts from IBKR are `Decimal`, EODHD prices are `float`.

| Type | Module | Used by |
|---|---|---|
| `Provider` | `clients/common/domain.py` | every `SecurityInformation` |
| `SecurityInformation` | `clients/common/domain.py` | `positions_to_security_information`, `ibkr_to_eodhd_security_information`, `eodhd_to_ibkr_security_information`, `latest_price` |
| `AccountInformation` | `clients/interactive_brokers/domain.py` | `get_account_information`, `print_account_information` |
| `PortfolioPosition` | `clients/interactive_brokers/domain.py` | `get_positions`, `print_positions`, `positions_to_security_information` |
| `Symbol` | `clients/eodhd/domain.py` | `get_symbols_by_ticker`, `get_symbols_by_isin`, `get_symbols_in_exchange` |
| `EndOfDayPrice` | `clients/eodhd/domain.py` | `latest_price` |

## Common

### `Provider`
```python
class Provider(Enum):
    IBKR = "IBKR"
    EODHD = "EODHD"
```
Says whose identifiers a `SecurityInformation` holds. Functions check it and raise `ValueError` on the wrong provider (e.g. `latest_price` only accepts `EODHD`).

### `SecurityInformation`
```python
@dataclass
class SecurityInformation:
    provider: Provider
    symbol: str
    exchange: str
    currency: str
    isin: Optional[str] = None
    contract_id: Optional[int] = None
```
The one identity of a security across the app, expressed in a given provider's codes. It is the hand-off object between IBKR and EODHD: positions become `IBKR` instances, the mapping functions convert between providers via the ISIN, and EODHD instances feed market data calls.
- `symbol` — IBKR symbol or EODHD ticker; they can differ (`GRE1` vs `GRE`).
- `exchange` — IBKR primary exchange (`SBF`) or EODHD exchange code (`PA`).
- `currency` — trading currency of the listing.
- `isin` — the cross-provider key; required by both conversion functions.
- `contract_id` — IBKR contract ID; `None` for EODHD.

## Interactive Brokers

### `AccountInformation`
```python
@dataclass
class AccountInformation:
    account: str
    currency: str
    net_liquidation: Decimal
    total_cash: Decimal
    buying_power: Decimal
    available_funds: Decimal
    excess_liquidity: Decimal
    maintenance_margin: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_cost: Optional[Decimal] = None
    gross_return: Optional[Decimal] = None
    net_return: Optional[Decimal] = None
    liquidation_value: Optional[Decimal] = None
```
Snapshot of one account in its base currency (`currency`), returned by `get_account_information`.
- `net_liquidation` — IBKR's figure: cash + market value, **no** exit costs. Printed as "Portfolio market value".
- `total_cash`, `buying_power`, `available_funds`, `excess_liquidity`, `maintenance_margin` — IBKR account summary values.
- `unrealized_pnl`, `realized_pnl` — account-level PnL.
- `total_cost` — cost of all positions (quantity × average cost, buy commissions included); `None` if any position is not in the base currency.
- `gross_return` — `unrealized_pnl / total_cost`, before exit costs.
- `net_return` — (net liquidation proceeds − `total_cost`) / `total_cost`, i.e. after IBKR's commission to close every position.
- `liquidation_value` — cash left after simulating the sale of everything (cash + proceeds − commissions). Printed as "Net liquidation".

The optional fields are filled by `get_account_information`; the rest come straight from IBKR.

### `PortfolioPosition`
```python
@dataclass
class PortfolioPosition:
    symbol: str
    exchange: str
    currency: str
    trading_class: str
    quantity: Decimal
    average_cost: Decimal
    total_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    unrealized_return: Optional[Decimal]
    contract_id: int
```
One open position, returned by `get_positions` and printed by `print_positions`; input to `positions_to_security_information`.
- `symbol`, `exchange`, `currency`, `trading_class`, `contract_id` — the IBKR contract (`exchange` is the primary exchange).
- `quantity` — shares held; negative for a short.
- `average_cost` — per share, including the buy commission; `total_cost` = `quantity` × `average_cost`.
- `market_price`, `market_value` — IBKR's valuation price and value (not necessarily the official close).
- `unrealized_pnl`, `realized_pnl` — per-position PnL.
- `unrealized_return` — `unrealized_pnl / |total_cost|`; `None` when the cost is zero.

## EODHD

### `Symbol`
```python
@dataclass
class Symbol:
    code: str
    name: str
    country: str
    exchange: str
    currency: str
    type: str
    isin: Optional[str]
```
One EODHD listing, as returned by the symbol searches.
- `code` — EODHD ticker (becomes `SecurityInformation.symbol`).
- `exchange` — EODHD exchange code (e.g. `XETRA`, `PA`, `US`).
- `type` — EODHD instrument type (e.g. `Common Stock`, `ETF`).
- `isin` — may be missing in EODHD's data.

### `EndOfDayPrice`
```python
@dataclass
class EndOfDayPrice:
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
```
One end-of-day price bar (OHLC + volume), returned by `latest_price`. `date` is ISO (`YYYY-MM-DD`); `adjusted_close` is adjusted for splits and dividends.

## Internal only

Not part of any public signature: `AccountInfo` (raw IBKR account data before conversion), `LiquidationEstimate` and `LiquidationSummary` (liquidation simulation results, surfaced only through `AccountInformation.liquidation_value` and `net_return`).
