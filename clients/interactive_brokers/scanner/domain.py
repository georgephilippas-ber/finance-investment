from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional, TypedDict

from numpy import array, full
from scipy.optimize import brentq

from helpers import latest_weekday

__all__ = ["Bond", "BondFilters", "BondQuote"]


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


def _add_months(day: date, months: int) -> date:
    month_index_ = day.month - 1 + months
    year_, month_ = day.year + month_index_ // 12, month_index_ % 12 + 1
    return date(year_, month_, min(day.day, monthrange(year_, month_)[1]))


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
    issuer: Optional[str] = None
    inflation_linked: bool = False
    callable: bool = False
    minimum_size: Decimal = Decimal(1)
    size_increment: Decimal = Decimal(1)
    quote: Optional[BondQuote] = None

    @property
    def is_zero_coupon(self) -> bool:
        return self.annual_coupon == 0

    def years_to_maturity(self, on: Optional[date] = None) -> Decimal:
        return Decimal((self.maturity - (on or latest_weekday())).days) / Decimal("365.25")

    def coupon_dates(self, after: date) -> List[date]:
        if self.maturity <= after:
            return []
        dates_: List[date] = []
        period_ = 0
        while (date_ := _add_months(self.maturity, -12 * period_)) > after:
            dates_.append(date_)
            period_ += 1
        return dates_[::-1]

    def dirty_price(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        # Quoted (clean) price plus the coupon accrued since the last coupon date, per 100 face.
        if self.quote is None:
            return None
        settlement_ = settlement or latest_weekday()
        dates_ = self.coupon_dates(settlement_)
        if not dates_:
            raise ValueError(f"{self.description} has matured.")
        previous_ = _add_months(dates_[0], -12)
        elapsed_ = Decimal((settlement_ - previous_).days) / Decimal((dates_[0] - previous_).days)
        return self.quote.price + self.annual_coupon * 100 * elapsed_

    def yield_without_reinvestment(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        # Annual return in % if coupons are kept as cash: face value plus all remaining coupons at maturity, against the
        # dirty price paid at settlement. A conservative floor under yield_to_maturity, which assumes reinvestment.
        settlement_ = settlement or latest_weekday()
        dirty_price_ = self.dirty_price(settlement_)
        if dirty_price_ is None:
            return None
        final_value_ = 100 + self.annual_coupon * 100 * len(self.coupon_dates(settlement_))
        growth_ = float(final_value_ / dirty_price_) ** (1 / float(self.years_to_maturity(settlement_))) - 1
        return Decimal(str(round(growth_ * 100, 4)))

    def yield_to_maturity(self, settlement: Optional[date] = None) -> Optional[Decimal]:
        # Annual yield in %: the IRR of paying the dirty price at settlement for the remaining cash flows, timed in
        # actual/365.25 years. Real (not nominal) yield for inflation-linked bonds.
        settlement_ = settlement or latest_weekday()
        dirty_price_ = self.dirty_price(settlement_)
        if dirty_price_ is None:
            return None
        dates_ = self.coupon_dates(settlement_)
        times_ = array([(date_ - settlement_).days / 365.25 for date_ in dates_])
        flows_ = full(len(dates_), float(self.annual_coupon) * 100)
        flows_[-1] += 100
        price_ = float(dirty_price_)
        rate_ = brentq(lambda rate_: (flows_ / (1 + rate_) ** times_).sum() - price_, -0.99, 10.0)
        return Decimal(str(round(rate_ * 100, 4)))
