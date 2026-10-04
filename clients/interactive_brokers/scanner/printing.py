from datetime import date
from decimal import Decimal
from typing import List, Optional

from babel.numbers import format_decimal

from helpers import latest_weekday
from printing import print_table

if __package__:
    from .domain import Bond
else:
    from domain import Bond

__all__ = ["print_bond"]


def _coupon(bond: Bond) -> str:
    return format(bond.annual_coupon, ".3%")


def _price(value: Optional[Decimal]) -> str:
    # Bond prices are per 100 face, not money, so no currency symbol.
    return format_decimal(value, format="#,##0.000", locale="en_US") if value is not None else "-"


def _yield(value: Optional[Decimal]) -> str:
    return f"{value:.3f}%" if value is not None else "-"


def _source(bond: Bond) -> str:
    if bond.quote is None:
        return "-"
    return "Live" if bond.quote.live else "Close"


def print_bond(bond: Bond, valuation_date: Optional[date] = None) -> None:
    valuation_date_ = valuation_date or latest_weekday()
    quote_ = bond.quote
    clean_price_ = quote_.price if quote_ is not None else None
    dirty_price_ = bond.dirty_price(valuation_date_)
    rows_: List[List[str]] = [
        ["Description", bond.description],
        ["ISIN", bond.isin or "-"],
        ["IBKR contract ID", str(bond.contract_id)],
        ["Bond type", bond.bond_type],
        ["Issuer", bond.issuer or "-"],
        ["Currency", bond.currency or "-"],
        ["Coupon", _coupon(bond)],
        ["Payment frequency", "Annual (assumed)"],
        ["Maturity", bond.maturity.isoformat()],
        ["Years to maturity", format(bond.years_to_maturity(valuation_date_), ".2f")],
        ["Inflation-linked", "Yes" if bond.inflation_linked else "No"],
        ["Callable", "Yes" if bond.callable else "No"],
        ["Rating", bond.rating or "-"],
        ["Minimum size", format(bond.minimum_size, ",f")],
        ["Size increment", format(bond.size_increment, ",f")],
        ["Price source", _source(bond)],
        ["Quote received", quote_.as_of.strftime("%Y-%m-%d %H:%M %Z") if quote_ is not None else "-"],
        ["Valuation date", valuation_date_.isoformat()],
        ["Clean price", _price(clean_price_)],
        ["Accrued interest", _price(dirty_price_ - clean_price_ if dirty_price_ is not None else None)],
        ["Dirty price", _price(dirty_price_)],
        ["Yield to maturity (real)" if bond.inflation_linked else "Yield to maturity",
         _yield(bond.yield_to_maturity(valuation_date_))],
        ["Yield, no reinvestment (real)" if bond.inflation_linked else "Yield, no reinvestment",
         _yield(bond.yield_without_reinvestment(valuation_date_))],
    ]
    print_table(["Field", "Value"], rows_, first_right_aligned_column=1, separators_after=(5, 12, 14, 17),
                title=bond.description)
