from dataclasses import dataclass
from typing import Optional


@dataclass
class IdentifierMapping:
    symbol: str
    isin: Optional[str]
    figi: Optional[str]
    lei: Optional[str]
    cusip: Optional[str]
    cik: Optional[str]
