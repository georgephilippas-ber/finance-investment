# Interactive Brokers client

`clients/interactive_brokers/client.py` — talks to IB Gateway / TWS through `ib_async`. Connections are read-only by default; nothing here places orders.

Connection settings come from `IBKR_HOST`, `IBKR_PORT`, `IBKR_CLIENT_ID` (env / `.env`), defaulting to `127.0.0.1`, `4001`, `1`.

## `connect`
```python
async def connect(*, host: Optional[str] = None, port: Optional[int] = None, client_id: Optional[int] = None, readonly: bool = True, timeout: float = 10) -> IB
```
Opens a connection to the gateway and returns the `IB` session.
- `host`, `port`, `client_id` — override the env/default settings.
- `readonly` — keep `True` unless orders must be placed.
- `timeout` — seconds to wait for the connection.

## `disconnect`
```python
def disconnect(ib: IB) -> None
```
Closes the session.

## `get_account_information`
```python
async def get_account_information(ib: IB, account: Optional[str] = None, *, limit_discount: Decimal = Decimal(0), timeout: float = 50) -> AccountInformation
```
Account summary in the base currency: net liquidation, cash, buying power, margin, realized/unrealized PnL, cost of positions, gross and net return, and the cash left after liquidating everything (`liquidation_value`).
- `account` — account ID; may be omitted when only one account is managed.
- `limit_discount` — limit price below market used for the liquidation estimate (`0` = at market).
- `timeout` — seconds per IBKR request.

Runs a what-if order per position (no order placed) to get IBKR's commission for closing it at the limit price, rounded to the venue's tick size. Raises if a position has no market price, IBKR returns no commission, or a position is not in the base currency.

## `get_positions`
```python
def get_positions(ib: IB, account: Optional[str] = None) -> List[PortfolioPosition]
```
Open positions with quantity, average cost, total cost, market price/value, realized/unrealized PnL and return.
- `account` — as above.

## `positions_to_security_information`
```python
async def positions_to_security_information(ib: IB, positions: List[PortfolioPosition], *, timeout: float = 50) -> List[SecurityInformation]
```
Converts each `PortfolioPosition` into a `SecurityInformation` (same order) and fills its ISIN (and contract ID) from IBKR's contract details. Raises `LookupError` when there is no or more than one matching contract, or not exactly one ISIN.

## `print_account_information`
```python
def print_account_information(information: AccountInformation) -> None
```
Prints an `AccountInformation` as a grouped two-column table. Shows `liquidation_value` as "Net liquidation" and IBKR's net liquidation as "Portfolio market value".

## `print_positions`
```python
def print_positions(positions: List[PortfolioPosition]) -> None
```
Prints a list of `PortfolioPosition` as a table with a row count.

## `print_full_account_information`
```python
async def print_full_account_information(ib: IB, account: Optional[str] = None, *, limit_discount: Decimal = Decimal(0), timeout: float = 50) -> None
```
Fetches and prints the account summary (`get_account_information` → `print_account_information`) followed by the positions table (`get_positions` → `print_positions`). Parameters are passed through to `get_account_information`; `account` also to `get_positions`.
