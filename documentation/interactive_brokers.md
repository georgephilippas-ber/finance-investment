# Interactive Brokers client

`clients/interactive_brokers/client.py` — reads an account through IB Gateway / TWS using `ib_async`.

- Connections are read-only by default. Nothing here places orders; commissions come from what-if previews.
- Connection settings: `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID` (environment or `.env`), defaulting to `127.0.0.1`, `4001`, `1`. Use port `4002` for a paper account.
- `account` parameters may be omitted when the session manages exactly one account; otherwise pass the account ID (`ValueError` if missing or unknown).
- `timeout` parameters are seconds per IBKR request.
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
async def get_account_information(ib: IB, account: Optional[str] = None, *, limit_discount: Decimal = Decimal(0), timeout: float = 50) -> AccountInformation
```
Returns an [`AccountInformation`](domain.md#accountinformation) in the account's base currency: IBKR's summary values plus cost of positions, gross and net return, and the liquidation value.
- `limit_discount` — how far below market (above for shorts) the simulated closing orders are priced; `0` = at market, `Decimal("0.05")` = 5 % worse.

**Liquidation simulation.** For each position it runs a what-if limit order to close it — no order is placed. The limit is rounded to the venue's tick size, and IBKR's own commission for that order is used. Net proceeds feed `liquidation_value` and `net_return`.

**Errors.** Raises if a position has no market price, IBKR returns no commission, a position is not in the base currency (no FX conversion), or an account value is missing or ambiguous.

## Positions

### `get_positions`
```python
def get_positions(ib: IB, account: Optional[str] = None) -> List[PortfolioPosition]
```
Open positions as [`PortfolioPosition`](domain.md#portfolioposition)s: quantity, cost, IBKR market price and value, PnL, holding-period return, and — from the [position tracker](position_tracker.md) — open date and annualized return (only after a year). Reads the portfolio already streamed to the session; no extra IBKR request. Without a tracker database, key or entry for a contract, the open date and annualized return are `None`.

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
Prints a two-column table in groups: account and currency; portfolio market value and net liquidation; gross return, net return and unrealized PnL; cash and margin figures; realized PnL.

Labels differ from field names: `net_liquidation` is printed as **Portfolio market value** and `liquidation_value` as **Net liquidation**.

### `print_positions`
```python
def print_positions(positions: List[PortfolioPosition]) -> None
```
Prints one row per position and a row count. Columns: Contract ID, Opened, Symbol, Exchange, Quantity, Total cost, Market price, Market value, Unrealized PnL, Return (`unrealized_hpr`), Annual Return (`unrealized_annualized_return`). Missing values are shown as `-`.

### `print_full_account_information`
```python
async def print_full_account_information(ib: IB, account: Optional[str] = None, *, limit_discount: Decimal = Decimal(0), timeout: float = 50) -> None
```
Fetches and prints both tables: `get_positions` → `print_positions`, then `get_account_information` → `print_account_information`, so the account summary comes last. Parameters are passed through.
