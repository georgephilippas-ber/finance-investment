from dataclasses import dataclass
from typing import Optional


@dataclass
class Symbol:
    code: str
    name: str
    country: str
    exchange: str
    currency: str
    type: str
    isin: Optional[str]


@dataclass
class EodCandle:
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
