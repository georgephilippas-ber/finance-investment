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
