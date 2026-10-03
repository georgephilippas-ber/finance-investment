from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Provider(Enum):
    IBKR = "IBKR"
    EODHD = "EODHD"


@dataclass
class SecurityInformation:
    provider: Provider
    symbol: str
    exchange: str
    currency: str
    isin: Optional[str] = None
    contract_id: Optional[int] = None


@dataclass
class EndOfDayPrice:
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
