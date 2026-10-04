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

__all__ = ["print_bond", "print_bonds"]


def _coupon(bond: Bond) -> str:
    return format(bond.annual_coupon, ".3%")


def _price(value: Optional[Decimal]) -> str:
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
        ["Years to maturity", format(bond.years_to_maturity(valuation_date_), ".2f")],
        ["Yield to maturity (real)" if bond.inflation_linked else "Yield to maturity",
         _yield(bond.yield_to_maturity(valuation_date_))],
        ["Yield, no reinvestment (real)" if bond.inflation_linked else "Yield, no reinvestment",
         _yield(bond.yield_without_reinvestment(valuation_date_))],
        ["Maturity", bond.maturity.isoformat()],
        ["Payment frequency", "Annual (assumed)"],
        ["Inflation-linked", "Yes" if bond.inflation_linked else "No"],
        ["Callable", "Yes" if bond.callable else "No"],
        ["Minimum size", format(bond.minimum_size, ",f")],
        ["Size increment", format(bond.size_increment, ",f")],
        ["Price source", _source(bond)],
        ["Quote received", quote_.as_of.strftime("%Y-%m-%d %H:%M %Z") if quote_ is not None else "-"],
        ["Valuation date", valuation_date_.isoformat()],
        ["Clean price", _price(clean_price_)],
        ["Accrued interest", _price(dirty_price_ - clean_price_ if dirty_price_ is not None else None)],
        ["Dirty price", _price(dirty_price_)],
    ]
    print_table(["Field", "Value"], rows_, first_right_aligned_column=1, separators_after=(5, 10, 13, 15, 18),
                title=bond.description)


def print_bonds(bonds: List[Bond], valuation_date: Optional[date] = None, *, title: str = "BONDS") -> None:
    valuation_date_ = valuation_date or latest_weekday()
    headers_: List[str] = ["Contract ID", "Name", "ISIN", "Clean price", "Coupon", "Years to maturity",
                           "Yield to maturity", "Yield, no reinvestment"]
    rows_: List[List[str]] = [
        [
            str(bond_.contract_id),
            bond_.description,
            bond_.isin or "-",
            _price(bond_.quote.price if bond_.quote is not None else None),
            _coupon(bond_),
            format(bond_.years_to_maturity(valuation_date_), ".2f"),
            _yield(bond_.yield_to_maturity(valuation_date_)),
            _yield(bond_.yield_without_reinvestment(valuation_date_)),
        ]
        for bond_ in bonds
    ]
    print_table(headers_, rows_, first_right_aligned_column=3, title=title)
    print(f"({len(rows_)} {'row' if len(rows_) == 1 else 'rows'})")
