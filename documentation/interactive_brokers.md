# Interactive Brokers client

`clients/interactive_brokers/client.py` — reads an account through IB Gateway / TWS using `ib_async`.

- Connections are read-only by default. Nothing here places orders; exit commissions are estimated with
  [`get_commission`](#get_commission) from IBKR's fixed schedule.
- Connection settings: `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID` from the environment, defaulting to `127.0.0.1`,
  `4001`, `1`. The entry-point scripts load `.env`; library callers must load it themselves if needed. Set the
  port to the API socket port configured in your Gateway or TWS; `4002` is the paper Gateway convention.
- `account` parameters may be omitted when the session manages exactly one account; otherwise pass the account ID (`ValueError` if missing or unknown).
- `timeout` parameters are seconds per IBKR request; they default to `DEFAULT_REQUEST_TIMEOUT` (50) and, for `connect`,
  `DEFAULT_CONNECT_TIMEOUT` (10), both in `configuration.py`.
- Open dates come from the [position tracker](position_tracker.md) (`IBKR_POSITION_TRACKER_KEY`), not from IBKR.

## Connection

### `connect`
```python
async def connect(*, host: Optional[str] = None, port: Optional[int] = None, client_id: Optional[int] = None, readonly: bool = True, timeout: float = 10) -> IB
```
Opens a session and returns the `IB` object every other function takes.
- `host`, `port`, `client_id` — override the environment / defaults.
- `readonly` — keep `True` unless orders must be placed.
- `timeout` — seconds to wait for the connection.

### `disconnect`
```python
def disconnect(ib: IB) -> None
```
Closes the session. Call it in a `finally` block.

## Account

### `get_account_information`
```python
async def get_account_information(ib: IB, account: Optional[str] = None, *, timeout: float = 50) -> AccountInformation
```
Returns an [`AccountInformation`](domain.md#accountinformation) in the account's base currency: IBKR's summary values plus cost of positions, gross and net return, and the liquidation value.

**Liquidation estimate.** For each nonzero position, net proceeds are IBKR's market value less
[`get_commission`](#get_commission) for closing the whole position at IBKR's market price. No IBKR request is
made for this step. The sum feeds `liquidation_value` and `net_return`. Spread, slippage and taxes are not
included, so the actual proceeds of a sale can be lower.

**Scope.** There is no contract-multiplier handling or instrument-type guard in this calculation. Signed long
and short costs can also cancel in the account return denominator. Use the estimates for long stocks/ETFs in
the base currency. These are open-position estimates, not historical account performance; see the
[exact formulas](domain.md#accountinformation).

**Missing values.** `liquidation_value` and `net_return` are `None` (printed `-`) if any position is not in
the base currency (no FX conversion), has a nonfinite market price or value, or is in a currency without a
commission schedule.

**Errors.** Raises if a required account value is missing or ambiguous. Request failures and timeouts propagate.

### `get_commission`
```python
def get_commission(quantity: Decimal, price: Decimal, currency: str) -> Decimal
```
IBKR Pro fixed-rate commission for one stock or ETF order of `|quantity|` shares at `price`, in `currency`,
rounded half up to cents. The sign of `quantity` (buy or sell) does not matter.

| Currency | Commission | Source |
|---|---|---|
| `EUR` | 0.05 % of order value, minimum €3 | matches IBKR what-if previews on Xetra and Euronext Paris |
| `USD` | $0.005 per share, minimum $1, maximum 1 % of order value | IBKR's published fixed schedule |

Other currencies raise `LookupError`. Exchange, regulatory and clearing fees, stamp duty and financial
transaction taxes are not modelled; check IBKR's current schedule before relying on these rates.

## Positions

### `get_positions`
```python
def get_positions(ib: IB, account: Optional[str] = None) -> List[PortfolioPosition]
```
Positions from the session's cached portfolio as [`PortfolioPosition`](domain.md#portfolioposition)s: quantity,
cost, IBKR market price and value, PnL, unrealized holding-period return, and — from the
[position tracker](position_tracker.md) — open date and an annualized estimate. There is no extra IBKR request.

Annualization uses the quantity-weighted age of the tracked lots, not just the earliest open date. The result
is `None` if that age is below 365 days, tracked total quantity is nonpositive, HPR is unavailable or at most
−100 %, or holding data is unavailable. Multiple purchase dates make this an approximation, not a
money-weighted or time-weighted return. Recorded quantities are not checked against the broker position.

Without a tracker database, key, or matching entry, the opening date and estimate are `None`. SQLite
`OperationalError` and missing-key `RuntimeError` are also suppressed this way. Malformed-key and decryption
errors are not generally suppressed; see [key behavior](position_tracker.md).

### `get_positions_as_security_information`
```python
async def get_positions_as_security_information(ib: IB, account: Optional[str] = None, *, timeout: float = 50) -> List[SecurityInformation]
```
The open positions (as `get_positions`, same order) as `Provider.IBKR` [`SecurityInformation`](domain.md#securityinformation)s, with `isin` and `contract_id` filled from IBKR's contract details (one request per position). This is the starting point for [mapping to EODHD](mappings.md).

Raises `LookupError` if a position has no or several matching contracts, or not exactly one ISIN; the whole call fails rather than returning a partial list.

## Printing

### `print_account_information`
```python
def print_account_information(information: AccountInformation) -> None
```
Titled **ACCOUNT SUMMARY** in the table's top row.
Prints a two-column table in groups: account and currency; portfolio market value and net liquidation; gross return, net return and unrealized PnL; cash and margin figures; realized PnL.

Labels differ from field names: IBKR's `net_liquidation` is printed as **Portfolio market value** (this includes
cash), and the locally estimated `liquidation_value` is printed as **Net liquidation**. The latter is an
estimate after `get_commission` exit commissions, not IBKR's reported `NetLiquidation` value.

Amounts are formatted with Babel in the account's currency (`€307.57`): rounded half up to cents, and shown compactly from one million (`€1.53M`, `€2.4B`). Returns are percentages; missing values are shown as `-`.

### `print_positions`
```python
def print_positions(positions: List[PortfolioPosition]) -> None
```
Titled **OPEN POSITIONS** in the table's top row.
Prints one row per position and a row count. Columns: Contract ID, Opened, Symbol, Exchange, Quantity, Total cost, Market price, Market value, Unrealized PnL, Return (`unrealized_hpr`), Annual Return (`unrealized_annualized_return`). Amounts (total cost, market price, market value, unrealized PnL) are formatted like the account summary, in each position's own currency. Missing values are shown as `-`.

### `print_full_account_information`
```python
async def print_full_account_information(ib: IB, account: Optional[str] = None, *, timeout: float = 50) -> None
```
Fetches and prints both tables: `get_account_information` → `print_account_information`, then `get_positions` →
`print_positions`, so the account summary comes first. Parameters are passed through. If account retrieval
fails, neither table is printed; call `get_positions` and `print_positions`
separately when only the positions table is needed.
