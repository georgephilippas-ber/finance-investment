# Domain

Data structures that public functions take or return. All are dataclasses except the `Provider` enum. IBKR amounts are `Decimal`; EODHD prices are `float`.

| Type | Module | Returned by | Taken by |
|---|---|---|---|
| `Provider` | `clients/common/domain.py` | — | every `SecurityInformation` |
| `SecurityInformation` | `clients/common/domain.py` | `get_positions_as_security_information`, `get_security_information_by_ticker` / `_by_isin` / `_in_exchange`, `SecurityInformationMapping` methods | `SecurityInformationMapping` methods, `get_latest_price` |
| `EndOfDayPrice` | `clients/common/domain.py` | `get_latest_price` | — |
| `AccountInformation` | `clients/interactive_brokers/domain.py` | `get_account_information` | `print_account_information` |
| `PortfolioPosition` | `clients/interactive_brokers/domain.py` | `get_positions` | `print_positions` |

## Common

### `Provider`
```python
class Provider(Enum):
    IBKR = "IBKR"
    EODHD = "EODHD"
```
Whose identifiers a `SecurityInformation` holds. Functions check it and raise `ValueError` on the wrong provider (e.g. `get_latest_price` accepts only `EODHD`).

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
The single identity of a security across the app, in one provider's codes. It is the hand-off object between providers: IBKR positions become `IBKR` instances, EODHD lookups return `EODHD` instances, and `SecurityInformationMapping` converts between them via the ISIN.
- `symbol` — IBKR symbol or EODHD ticker; they can differ (`GRE1` vs `GRE`).
- `exchange` — IBKR primary exchange (`SBF`) or EODHD exchange code (`PA`).
- `currency` — trading currency of the listing.
- `isin` — the cross-provider key; required for conversion.
- `contract_id` — IBKR contract ID; always `None` for EODHD.

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
One daily price bar, returned by `get_latest_price`. `date` is ISO (`YYYY-MM-DD`); `adjusted_close` is adjusted for splits and dividends. Provider-neutral, so other price sources can return it too.

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
Snapshot of one account in its base currency (`currency`).

From IBKR:
- `net_liquidation` — cash + market value, **without** exit costs. Printed as "Portfolio market value".
- `total_cash`, `buying_power`, `available_funds`, `excess_liquidity`, `maintenance_margin` — account summary values.
- `unrealized_pnl`, `realized_pnl` — account-level PnL.

Computed by `get_account_information` (`None` when not computable):
- `total_cost` — cost of all positions (quantity × average cost, buy commissions included); `None` if any position is not in the base currency.
- `gross_return` — `unrealized_pnl / total_cost`: after buy costs, before exit costs.
- `net_return` — (net liquidation proceeds − `total_cost`) / `total_cost`: after IBKR's commission to close every position.
- `liquidation_value` — cash after simulating the sale of everything (cash + proceeds − commissions). Printed as "Net liquidation".

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
One open position.
- `symbol`, `exchange`, `currency`, `trading_class`, `contract_id` — the IBKR contract; `exchange` is the primary exchange.
- `quantity` — shares held; negative for a short.
- `average_cost` — per share, buy commission included; `total_cost` = `quantity` × `average_cost`.
- `market_price`, `market_value` — IBKR's valuation price and value (not necessarily the official close).
- `unrealized_pnl`, `realized_pnl` — position PnL.
- `unrealized_return` — `unrealized_pnl / |total_cost|`; `None` when the cost is zero.

## Internal

Used only inside their package and absent from public signatures:
- `_Symbol` (`clients/eodhd/domain.py`) — raw EODHD symbol record, converted to `SecurityInformation` before leaving the EODHD client.
- `AccountInfo` (`clients/interactive_brokers/domain.py`) — raw IBKR account data before conversion.
- `LiquidationEstimate`, `LiquidationSummary` (`clients/interactive_brokers/domain.py`) — liquidation simulation results, surfaced through `AccountInformation.liquidation_value` and `net_return`.
