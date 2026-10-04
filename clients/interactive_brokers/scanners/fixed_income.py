from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from logging import getLogger
from typing import List, Optional, Tuple, Unpack

from ib_async import IB, ContractDetails

if __package__:
    from ._shared import get_isin, get_market_prices, resolve_legal_entities, scan_details
    from .domain import PERCENT, SCANNER_ROW_LIMIT, Bond, BondFilters, BondQuote
else:
    from _shared import get_isin, get_market_prices, resolve_legal_entities, scan_details
    from domain import PERCENT, SCANNER_ROW_LIMIT, Bond, BondFilters, BondQuote

__all__ = ["interactive_brokers_scan_bonds", "quote_bonds"]

_logger = getLogger(__name__)

_IBKR_DATE_FORMAT = "%Y%m%d"
_IBKR_DATE_LENGTH = len("YYYYMMDD")


def _parse_description(description: str) -> Tuple[Decimal, date]:
    _, *coupon_parts_, maturity_ = description.split()
    coupon_ = Decimal(0)
    for part_ in coupon_parts_:
        fraction_ = Fraction(part_)
        coupon_ += Decimal(fraction_.numerator) / Decimal(fraction_.denominator)
    return coupon_, datetime.strptime(maturity_, "%m/%d/%y").date()


def _to_bond(details: ContractDetails, currency: Optional[str]) -> Bond:
    contract_ = details.contract
    currency_ = contract_.currency or currency
    if details.maturity:
        coupon_ = Decimal(str(details.coupon))
        maturity_ = datetime.strptime(details.maturity[:_IBKR_DATE_LENGTH], _IBKR_DATE_FORMAT).date()
    else:
        coupon_, maturity_ = _parse_description(details.descAppend)
    return Bond(
        contract_id=contract_.conId,
        isin=get_isin(details),
        description=details.descAppend,
        bond_type=contract_.tradingClass,
        currency=currency_,
        annual_coupon=coupon_ / PERCENT,  # IBKR and descAppend quote coupons in percent
        maturity=maturity_,
        inflation_linked=details.evRule.startswith("factor"),  # index-ratio factor, e.g. DBRI
        callable=details.callable,
        minimum_size=Decimal(str(details.minSize)),
        size_increment=Decimal(str(details.sizeIncrement)),
    )


async def interactive_brokers_scan_bonds(
        client_: IB, *,
        instrument: str,
        location: str,
        scan_code: str,
        rows: int = SCANNER_ROW_LIMIT,
        **filters: Unpack[BondFilters],
) -> List[Bond]:
    details_ = await scan_details(client_, instrument, location, scan_code, rows, dict(filters))

    bonds_: List[Bond] = []
    for item_ in details_:
        try:
            bonds_.append(_to_bond(item_, filters.get("currencyLike")))
        except ValueError:
            _logger.warning(
                f"Skipping conId {item_.contract.conId}: cannot read coupon/maturity from {item_.descAppend!r}.")

    entities_ = await resolve_legal_entities([bond_.isin for bond_ in bonds_])
    return [replace(bond_, legal_entity=entity_) for bond_, entity_ in zip(bonds_, entities_)]


async def quote_bonds(ib: IB, bonds: List[Bond]) -> List[Bond]:
    prices_ = await get_market_prices(ib, [bond_.contract_id for bond_ in bonds])
    return [
        replace(bond_, quote=BondQuote(*prices_[bond_.contract_id]) if bond_.contract_id in prices_ else None)
        for bond_ in bonds
    ]
