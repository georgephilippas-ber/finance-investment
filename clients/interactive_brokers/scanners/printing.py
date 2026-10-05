from datetime import date
from decimal import Decimal
from typing import List, Optional

from babel.numbers import format_decimal

from clients.interactive_brokers.configuration import YIELD_DECIMALS
from helpers import latest_weekday
from printing import print_grouped_table, print_row_count, print_table

if __package__:
    from .domain import SCANNER_ROW_LIMIT, Bond
else:
    from domain import SCANNER_ROW_LIMIT, Bond

__all__ = ["print_bond", "print_bonds", "print_bonds_table"]


def _coupon(bond: Bond) -> str:
    return format(bond.annual_coupon, ".3%")


def _price(value: Optional[Decimal]) -> str:
    return format_decimal(value, format="#,##0.000", locale="en_US") if value is not None else "-"


def _yield(value: Optional[Decimal]) -> str:
    return f"{value:.{YIELD_DECIMALS}f}%" if value is not None else "-"


def _callable(bond: Bond) -> str:
    return "Yes" if bond.callable else "No"


def _source(bond: Bond) -> str:
    if bond.quote is None:
        return "-"
    return "Live" if bond.quote.live else "Close"


def print_bond(bond: Bond, valuation_date: Optional[date] = None) -> None:
    valuation_date_ = valuation_date or latest_weekday()
    quote_ = bond.quote
    clean_price_ = quote_.price if quote_ is not None else None
    dirty_price_ = bond.dirty_price(valuation_date_)
    entity_ = bond.legal_entity
    groups_: List[List[List[str]]] = [
        [
            ["Description", bond.description],
            ["ISIN", bond.isin or "-"],
            ["IBKR contract ID", str(bond.contract_id)],
            ["Bond type", bond.bond_type],
            ["Currency", bond.currency or "-"],
        ],
        [
            ["Issuer", entity_.legal_name if entity_ is not None else "-"],
            ["LEI", entity_.lei if entity_ is not None else "-"],
            ["Issuer country", entity_.country if entity_ is not None else "-"],
            ["LEI status", entity_.status if entity_ is not None else "-"],
        ],
        [
            ["Coupon", _coupon(bond)],
            ["Years to maturity", format(bond.years_to_maturity(valuation_date_), ".2f")],
            ["Yield to maturity (real)" if bond.inflation_linked else "Yield to maturity",
             _yield(bond.yield_to_maturity(valuation_date_))],
            ["Yield, no reinvestment (real)" if bond.inflation_linked else "Yield, no reinvestment",
             _yield(bond.yield_without_reinvestment(valuation_date_))],
            ["Maturity", bond.maturity.isoformat()],
        ],
        [
            ["Payment frequency", "Annual (assumed)"],
            ["Inflation-linked", "Yes" if bond.inflation_linked else "No"],
            ["Callable", _callable(bond)],
        ],
        [
            ["Minimum size", format(bond.minimum_size, ",f")],
            ["Size increment", format(bond.size_increment, ",f")],
        ],
        [
            ["Price source", _source(bond)],
            ["Quote received", quote_.as_of.strftime("%Y-%m-%d %H:%M %Z") if quote_ is not None else "-"],
            ["Valuation date", valuation_date_.isoformat()],
        ],
        [
            ["Clean price", _price(clean_price_)],
            ["Accrued interest", _price(dirty_price_ - clean_price_ if dirty_price_ is not None else None)],
            ["Dirty price", _price(dirty_price_)],
        ],
    ]
    print_grouped_table(["Field", "Value"], groups_, title=bond.description)


def print_bonds(bonds: List[Bond], valuation_date: Optional[date] = None, *, max_rows: Optional[int] = None) -> None:
    valuation_date_ = valuation_date or latest_weekday()
    for index_, bond_ in enumerate(bonds[:max_rows]):
        if index_:
            print()
        print_bond(bond_, valuation_date_)


def print_bonds_table(bonds: List[Bond], valuation_date: Optional[date] = None, *, title: str = "BONDS",
                      has_lei: bool = False, max_rows: Optional[int] = None) -> None:
    valuation_date_ = valuation_date or latest_weekday()
    shown_ = [bond_ for bond_ in bonds if not has_lei or bond_.legal_entity is not None]
    headers_: List[str] = ["Contract ID", "Name", "Issuer", "ISIN", "Clean price", "Coupon", "Years to maturity",
                           "Yield to maturity", "Yield, no reinvestment", "Callable"]
    rows_: List[List[str]] = [
        [
            str(bond_.contract_id),
            bond_.description,
            bond_.legal_entity.legal_name if bond_.legal_entity is not None else "-",
            bond_.isin or "-",
            _price(bond_.quote.price if bond_.quote is not None else None),
            _coupon(bond_),
            format(bond_.years_to_maturity(valuation_date_), ".2f"),
            _yield(bond_.yield_to_maturity(valuation_date_)),
            _yield(bond_.yield_without_reinvestment(valuation_date_)),
            _callable(bond_),
        ]
        for bond_ in shown_[:max_rows]
    ]
    count_ = _instrument_count(len(shown_), len(bonds), has_lei)
    print_table(headers_, rows_, first_right_aligned_column=headers_.index("Clean price"), title=f"{title} ({count_})")
    print_row_count(len(rows_))


def _instrument_count(shown: int, total: int, filtered: bool) -> str:
    total_ = f"{'> ' if total == SCANNER_ROW_LIMIT else ''}{total}"
    noun_ = "instrument" if total == 1 else "instruments"
    return f"{shown} of {total_} {noun_}" if filtered else f"{total_} {noun_}"
