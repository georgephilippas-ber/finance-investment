# Position tracker

`clients/interactive_brokers/position_tracker.py` — records when each position was opened, which IBKR does not report. Each purchase is a [`Lot`](domain.md#lot): contract ID, open date and quantity.

- Stored in SQLite at `domain/positions/positions.sqlite`, table `position_tracker`, keyed on (contract ID, open date).
- **Contract IDs are encrypted** with AES-SIV before they are stored, using the key in `IBKR_POSITION_TRACKER_KEY` (`.env`, read by `configuration.position_tracker_key()`). Encryption is deterministic, so lookups by contract ID work; a wrong key fails with `InvalidTag`.
- **Open dates and quantities are not encrypted.** Rows of the same contract share the same encrypted ID.
- **Back up the key** outside the project: without it the stored contract IDs cannot be recovered.
- Call `load_dotenv()` before using the tracker so the key is available.

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

Running the module (`python3 -m clients.interactive_brokers.position_tracker`) executes its `_main`, which **replaces all stored lots** with the ones listed there and prints them.
