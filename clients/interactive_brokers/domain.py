from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ib_async import AccountValue, PortfolioItem, Position


@dataclass
class AccountInfo:
    account: str
    summary: List[AccountValue]
    values: List[AccountValue]
    positions: List[Position]
    portfolio: List[PortfolioItem]


@dataclass
class AccountInformation:
    account: str
    currency: str
    net_liquidation: Decimal
    total_cash: Decimal
    buying_power: Decimal
    available_funds: Decimal
    excess_liquidity: Decimal
    maintenance_margin: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal


@dataclass
class PortfolioPosition:
    symbol: str
    exchange: str
    currency: str
    trading_class: str
    quantity: Decimal
    average_cost: Decimal
    total_cost: Decimal
    contract_id: int


@dataclass
class SecurityInformation:
    symbol: str
    exchange: str
    currency: str
    isin: Optional[str] = None
    contract_id: Optional[int] = None
