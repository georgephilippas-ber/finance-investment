# Position tracker

`clients/interactive_brokers/position_tracker.py` — manually records opening dates, which are absent from the
portfolio snapshot used by this client. Each [`Lot`](domain.md#lot) stores a contract ID, open date and quantity;
one row represents the total recorded for that contract on that date.

- Stored in SQLite at `domain/positions/positions.sqlite`, table `position_tracker`, keyed on (contract ID, open date).
- **Contract IDs are encrypted** with AES-SIV before they are stored, using `IBKR_POSITION_TRACKER_KEY` from the
  environment. Encryption is deterministic, so lookups by contract ID work. With a different valid key,
  `by_contract_id` normally finds no matching rows; `all()` raises `InvalidTag` when it tries to decrypt existing
  rows encrypted with the original key. A malformed key can raise a decoding or key-length error.
- **Open dates and quantities are not encrypted.** Rows of the same contract share the same encrypted ID.
- **Back up the key** outside the project: without it the stored contract IDs cannot be recovered.
- Set the key in the environment, or call `load_dotenv()` before using the tracker. The configuration function
  does not load `.env` itself. Reuse the existing database's key; generating a new key does not re-encrypt old rows.

[`get_positions`](interactive_brokers.md#get_positions) reads the tracker to fill `PortfolioPosition.opened` and `unrealized_annualized_return`.

## `PositionTracker`

```python
class PositionTracker:
    @staticmethod
    def create_database() -> None
    @staticmethod
    def add(contract_id: int, opened: date, quantity: Decimal) -> None
    @staticmethod
    def remove(contract_id: int, opened: Optional[date] = None) -> None
    @staticmethod
    def delete_all() -> None
    @staticmethod
    def by_contract_id(contract_id: int) -> List[Lot]
    @staticmethod
    def all() -> DataFrame
    @staticmethod
    def quantity(contract_id: int) -> Decimal
```

All methods are static and work on the database at the module's `DEFAULT_PATH`.

| Method | Does |
|---|---|
| `create_database` | Creates `domain/positions/` and the table if missing; safe to call repeatedly. Required before first use. |
| `add` | Inserts a lot, or replaces the quantity of that contract's lot on that day (one entry per contract per day — record the day's total). |
| `remove` | Deletes one lot, or every lot of the contract when `opened` is omitted. |
| `delete_all` | Empties the table (the table and file remain). No confirmation. |
| `by_contract_id` | The contract's lots, oldest first. |
| `all` | Every lot as a DataFrame with `contract_id`, `opened`, `quantity` (as `int`, `date`, `Decimal`), sorted by contract and date; empty frame with those columns when there are none. |
| `quantity` | Sum of the contract's lot sizes — compare with IBKR's position quantity to spot unrecorded purchases. |

## Keeping lots consistent

The tracker does not import executions or adjust lots for sales, splits, or transfers. Maintain the remaining
quantities manually and compare `quantity(contract_id)` with the broker position. `get_positions` does not
perform that comparison before calculating the annualized estimate. Input dates and quantities are not
validated for future dates, positive quantities, or consistency with broker holdings.

Rows have no account ID, so holdings of the same contract in different accounts share the same tracker data.
The tracker stores no purchase prices, commissions, or dividend cash flows.

## Running the module

From the project root, `python3 -m clients.interactive_brokers.position_tracker` loads `.env`, prints all stored
lots, then prints the lookup for the hard-coded contract ID in `_main`. It does not insert, replace, or delete
lots, and it does not initialize the table. An existing table and the matching encryption key are required
to read stored data.
