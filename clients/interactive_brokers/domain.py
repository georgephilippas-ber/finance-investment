from dataclasses import dataclass
from datetime import date
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
    total_cost: Optional[Decimal] = None
    gross_return: Optional[Decimal] = None
    net_return: Optional[Decimal] = None
    liquidation_value: Optional[Decimal] = None


@dataclass
class PortfolioPosition:
    symbol: str
    exchange: str
    currency: str
    trading_class: str
    quantity: Decimal
    average_cost: Decimal
    total_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    unrealized_hpr: Optional[Decimal]
    opened: Optional[date]
    unrealized_annualized_return: Optional[Decimal]
    contract_id: int



@dataclass
class LiquidationEstimate:
    contract_id: int
    symbol: str
    currency: str
    quantity: Decimal
    market_price: Decimal
    limit_price: Decimal
    gross_proceeds: Decimal
    commission: Decimal
    net_proceeds: Decimal


@dataclass
class LiquidationSummary:
    account: str
    currency: str
    cash: Decimal
    positions: List[LiquidationEstimate]
    net_proceeds: Decimal
    cash_after_liquidation: Decimal
