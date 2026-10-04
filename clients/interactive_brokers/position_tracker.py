from base64 import urlsafe_b64decode, urlsafe_b64encode
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from sqlite3 import Connection, connect
from typing import List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from dotenv import load_dotenv
from pandas import DataFrame

from settings import PROJECT_ROOT

if __package__:
    from . import configuration
else:
    import configuration

__all__ = ["Lot", "PositionTracker"]

DEFAULT_PATH: Path = PROJECT_ROOT / "domain" / "positions" / "positions.sqlite"


@dataclass(frozen=True)
class Lot:
    contract_id: int
    opened: date
    quantity: Decimal


class PositionTracker:
    @staticmethod
    def create_database() -> None:
        DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(PositionTracker._connect()) as connection_, connection_:
            connection_.execute(
                """
                    CREATE TABLE IF NOT EXISTS position_tracker (
                        contract_id TEXT NOT NULL,
                        opened TEXT NOT NULL,
                        quantity TEXT NOT NULL,
                        PRIMARY KEY (contract_id, opened)
                    )
                """)

    @staticmethod
    def _connect() -> Connection:
        return connect(DEFAULT_PATH)

    @staticmethod
    def _encrypt(contract_id: int) -> str:
        cipher_ = AESSIV(configuration.position_tracker_key())
        return urlsafe_b64encode(cipher_.encrypt(str(contract_id).encode(), None)).decode()

    @staticmethod
    def _decrypt(token: str) -> int:
        cipher_ = AESSIV(configuration.position_tracker_key())
        return int(cipher_.decrypt(urlsafe_b64decode(token), None).decode())

    @staticmethod
    def add(contract_id: int, opened: date, quantity: Decimal) -> None:
        with closing(PositionTracker._connect()) as connection_, connection_:
            connection_.execute(
                "INSERT INTO position_tracker (contract_id, opened, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT (contract_id, opened) DO UPDATE SET quantity = excluded.quantity",
                (PositionTracker._encrypt(contract_id), opened.isoformat(), str(quantity)),
            )

    @staticmethod
    def remove(contract_id: int, opened: Optional[date] = None) -> None:
        with closing(PositionTracker._connect()) as connection_, connection_:
            if opened is None:
                connection_.execute("DELETE FROM position_tracker WHERE contract_id = ?",
                                    (PositionTracker._encrypt(contract_id),))
            else:
                connection_.execute("DELETE FROM position_tracker WHERE contract_id = ? AND opened = ?",
                                    (PositionTracker._encrypt(contract_id), opened.isoformat()))

    @staticmethod
    def delete_all() -> None:
        with closing(PositionTracker._connect()) as connection_, connection_:
            connection_.execute("DELETE FROM position_tracker")

    @staticmethod
    def _get(contract_id: Optional[int] = None) -> List[Lot]:
        query_ = "SELECT contract_id, opened, quantity FROM position_tracker"
        parameters_ = ()
        if contract_id is not None:
            query_ += " WHERE contract_id = ?"
            parameters_ = (PositionTracker._encrypt(contract_id),)
        with closing(PositionTracker._connect()) as connection_:
            rows_ = connection_.execute(query_, parameters_).fetchall()
        return sorted(
            (Lot(PositionTracker._decrypt(row_[0]), date.fromisoformat(row_[1]), Decimal(row_[2])) for row_ in rows_),
            key=lambda lot_: (lot_.contract_id, lot_.opened),
        )

    @staticmethod
    def by_contract_id(contract_id: int) -> List[Lot]:
        return PositionTracker._get(contract_id)

    @staticmethod
    def all() -> DataFrame:
        return DataFrame(
            [(lot_.contract_id, lot_.opened, lot_.quantity) for lot_ in PositionTracker._get()],
            columns=["contract_id", "opened", "quantity"],
        )

    @staticmethod
    def quantity(contract_id: int) -> Decimal:
        return sum((lot_.quantity for lot_ in PositionTracker.by_contract_id(contract_id)), Decimal(0))


def _main() -> None:
    load_dotenv()
    print(PositionTracker.all())


if __name__ == "__main__":
    _main()
