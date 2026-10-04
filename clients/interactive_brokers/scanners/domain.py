from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional, TypedDict

from numpy import array, full
from scipy.optimize import brentq

from clients.interactive_brokers.configuration import YIELD_DECIMALS
from clients.lei_resolver.domain import LegalEntity
from helpers import add_months, latest_weekday
from settings import MONTHS_PER_YEAR

__all__ = ["Bond", "BondFilters", "BondQuote", "DAYS_PER_YEAR", "FACE_VALUE", "PERCENT", "SCANNER_ROW_LIMIT"]

SCANNER_ROW_LIMIT = 50
FACE_VALUE = 100
PERCENT = 100
DAYS_PER_YEAR = Decimal("365.25")
_MINIMUM_YIELD = -0.99
_MAXIMUM_YIELD = 10.0


class BondFilters(TypedDict, total=False):
    maturityDateAbove: str  # YYYYMMDD
    maturityDateBelow: str  # YYYYMMDD
    bondVarCouponRateIs: Any
    issuerCountryIs: str
    currencyLike: str
    bondCreditRating: str  # "highGrade" or "highYield"
    bondCallableIs: Any
    bondDefaultedIs: Any
    excludeConvertible: Any
    bondAmtOutstandingAbove: Any  # millions of face value
    bondInitialSizeAbove: Any
    bondInitialSizeBelow: Any


@dataclass(frozen=True)
class BondQuote:
    price: Decimal  # clean price, in % of face value
    as_of: datetime
    live: bool  # False when the price is a previous close


@dataclass(frozen=True)
class Bond:
    contract_id: int
    isin: Optional[str]
    description: str
    bond_type: str
    currency: Optional[str]  # IBKR often leaves it empty for bonds
    annual_coupon: Decimal  # fraction of face value, e.g. 0.025 for 2.5%
    maturity: date  # coupons are treated as paid once a year, on the maturity anniversary
    inflation_linked: bool = False
    callable: bool = False
    minimum_size: Decimal = Decimal(1)
    size_increment: Decimal = Decimal(1)
    legal_entity: Optional[LegalEntity] = None
    quote: Optional[BondQuote] = None

    @property
    def is_zero_coupon(self) -> bool:
        return self.annual_coupon == 0

    def years_to_maturity(self, on: Optional[date] = None) -> Decimal:
        return Decimal((self.maturity - (on or latest_weekday())).days) / DAYS_PER_YEAR

    def coupon_dates(self, after: date) -> List[date]:
        if self.maturity <= after:
            return []
        dates_: List[date] = []
        period_ = 0
        while (date_ := add_months(self.maturity, -MONTHS_PER_YEAR * period_)) > after:
            dates_.append(date_)
            period_ += 1
        return dates_[::-1]

    def dirty_price(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        if self.quote is None:
            return None
        settlement_ = settlement or latest_weekday()
        dates_ = self.coupon_dates(settlement_)
        if not dates_:
            raise ValueError()
        previous_ = add_months(dates_[0], -MONTHS_PER_YEAR)
        elapsed_ = Decimal((settlement_ - previous_).days) / Decimal((dates_[0] - previous_).days)
        return self.quote.price + self.annual_coupon * FACE_VALUE * elapsed_

    def yield_without_reinvestment(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        settlement_ = settlement or latest_weekday()
        dirty_price_ = self.dirty_price(settlement_)
        if dirty_price_ is None:
            return None
        final_value_ = FACE_VALUE + self.annual_coupon * FACE_VALUE * len(self.coupon_dates(settlement_))
        growth_ = float(final_value_ / dirty_price_) ** (1 / float(self.years_to_maturity(settlement_))) - 1
        return Decimal(str(round(growth_ * PERCENT, YIELD_DECIMALS)))

    def yield_to_maturity(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        settlement_ = settlement or latest_weekday()
        dirty_price_ = self.dirty_price(settlement_)
        if dirty_price_ is None:
            return None
        dates_ = self.coupon_dates(settlement_)
        times_ = array([(date_ - settlement_).days / float(DAYS_PER_YEAR) for date_ in dates_])
        flows_ = full(len(dates_), float(self.annual_coupon) * FACE_VALUE)
        flows_[-1] += FACE_VALUE
        price_ = float(dirty_price_)
        rate_ = brentq(lambda rate_: (flows_ / (1 + rate_) ** times_).sum() - price_, _MINIMUM_YIELD, _MAXIMUM_YIELD)
        return Decimal(str(round(rate_ * PERCENT, YIELD_DECIMALS)))
