# Domain

Data structures that public functions take or return. All are dataclasses except the `Provider` enum. IBKR amounts are `Decimal`; EODHD prices are `float`.

| Type | Module | Returned by | Taken by |
|---|---|---|---|
| `Provider` | `clients/common/domain.py` | — | every `SecurityInformation` |
| `SecurityInformation` | `clients/common/domain.py` | `get_positions_as_security_information`, `get_security_information_by_ticker` / `_by_isin` / `_in_exchange`, `SecurityInformationMapping` methods | `SecurityInformationMapping` methods, `get_latest_price` |
| `EndOfDayPrice` | `clients/common/domain.py` | `get_latest_price` | — |
| `AccountInformation` | `clients/interactive_brokers/domain.py` | `get_account_information` | `print_account_information` |
| `PortfolioPosition` | `clients/interactive_brokers/domain.py` | `get_positions` | `print_positions` |
| `Lot` | `clients/interactive_brokers/position_tracker.py` | `PositionTracker.by_contract_id` | — |
| `Bond` | `clients/interactive_brokers/scanners/domain.py` | `interactive_brokers_scan_bonds`, `quote_bonds` | `quote_bonds`, `print_bond`, `print_bonds_table` |
| `BondQuote` | `clients/interactive_brokers/scanners/domain.py` | inside `Bond.quote` | — |
| `BondFilters` | `clients/interactive_brokers/scanners/domain.py` | — | `interactive_brokers_scan_bonds` |

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
- `symbol` — IBKR symbol or EODHD ticker; they can differ (IBKR `BP.` vs EODHD `BP`).
- `exchange` — IBKR primary exchange (`IBIS`) or EODHD exchange code (`XETRA`).
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

Computed fields:

- `total_cost` — sum of signed quantity × IBKR average cost for the current positions; `None` if a position's
  currency differs from the base currency.
- `gross_return` — `unrealized_pnl / abs(total_cost)`; `None` for zero cost.
- `net_return` — `(net_proceeds - total_cost) / abs(total_cost)`; `None` for zero cost or when the liquidation
  estimate is unavailable. `net_proceeds` sums each position's IBKR market value less its `get_commission`
  exit commission.
- `liquidation_value` — `total_cash + net_proceeds`; `None` if a position is not in the base currency, lacks a
  finite market price or value, or has no commission schedule. Printed as "Net liquidation".

Gross and net returns describe the current open positions. They do not measure historical account performance
or incorporate a transaction history, deposits, withdrawals, or a separate dividend cash-flow series. Signed
long and short costs can cancel, giving a zero or misleadingly small denominator. Exit commissions use the
stock/ETF schedule regardless of instrument type. These calculations currently assume long stock/ETF positions in the base currency;
the implementation does not enforce that instrument or position-direction restriction.

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
    unrealized_hpr: Optional[Decimal]
    opened: Optional[date]
    unrealized_annualized_return: Optional[Decimal]
    contract_id: int
    isin: Optional[str] = None
```
One open position.
- `symbol`, `exchange`, `currency`, `trading_class`, `contract_id` — the IBKR contract; `exchange` is the primary
  exchange, falling back to the contract's exchange when the primary exchange is empty.
- `isin` — from IBKR's contract details; `None` when it cannot be resolved. Filled by `get_positions`.
- `quantity` — IBKR's position quantity (shares for stocks/ETFs); negative for a short.
- `average_cost` — IBKR's `averageCost`, converted to `Decimal`; `total_cost` = signed `quantity` × `average_cost`.
- `market_price`, `market_value` — IBKR's valuation price and value (not necessarily the official close).
- `unrealized_pnl`, `realized_pnl` — position PnL.
- `unrealized_hpr` — unrealized holding-period return, `unrealized_pnl / |total_cost|` (not annualized); `None` when the cost is zero. Printed as "Return".
- `opened` — earliest open date recorded for the contract in the position tracker; `None` if it has no lots there.
- `unrealized_annualized_return` — `(1 + HPR) ** (365 / days) - 1`, where
  `days = sum(lot.quantity * (date.today() - lot.opened).days) / sum(lot.quantity)`.
  It is `None` when holding data or HPR is unavailable, tracked total quantity is nonpositive, the weighted
  age is below 365 days, or HPR is at most −100 %. Printed as "Annual Return".

The annualized figure is an approximation for positions accumulated on different dates. It uses quantities
and dates, not purchase cash flows, and is neither a money-weighted nor time-weighted return. Tracker quantities
are not reconciled automatically with current holdings. Sales, splits, and transfers require manual tracker
updates. Missing tracker data does not prevent the other position fields from being returned.

### `Lot`
```python
@dataclass(frozen=True)
class Lot:
    contract_id: int
    opened: date
    quantity: Decimal
```
One contract/date entry in the [position tracker](position_tracker.md): IBKR contract ID (decrypted), open date
and quantity. Same-day purchases share one entry whose quantity must be supplied as a total; `add` replaces
that total rather than incrementing it. A position recorded on several days has several lots; `get_positions`
derives `opened` and the annualized estimate from them. No purchase cost or account ID is stored.

## Scanners

`Bond`, `BondQuote` and `BondFilters` are documented with the functions that use them, in
[Scanners](scanners.md#data-structures). Like `Lot`, `Bond` and `BondQuote` are frozen. Bond prices are per 100 of
face value rather than amounts of money.

## Internal

Used only inside their package and absent from public signatures:
- `_Symbol` (`clients/eodhd/domain.py`) — raw EODHD symbol record, converted to `SecurityInformation` before leaving the EODHD client.
- `AccountInfo` (`clients/interactive_brokers/domain.py`) — raw IBKR account data before conversion.
