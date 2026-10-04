from asyncio import gather
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from logging import getLogger
from math import isnan, log10
from typing import List, Optional, Tuple, Unpack

from ib_async import IB, Contract, ContractDetails, LimitOrder, OrderState, ScannerSubscription, TagValue, Ticker

if __package__:
    from .domain import Bond, BondFilters, BondQuote
else:
    from domain import Bond, BondFilters, BondQuote

__all__ = ["get_face_value_per_unit", "quote_bonds", "scan_bonds"]

_logger = getLogger(__name__)


def _parse_description(description: str) -> Tuple[Decimal, date]:
    # IBKR leaves coupon/maturity empty for these bonds; descAppend carries them, e.g. "OBL 2 1/2 04/16/31".
    _, *coupon_parts_, maturity_ = description.split()
    coupon_ = Decimal(0)
    for part_ in coupon_parts_:
        fraction_ = Fraction(part_)
        coupon_ += Decimal(fraction_.numerator) / Decimal(fraction_.denominator)
    return coupon_, datetime.strptime(maturity_, "%m/%d/%y").date()


def _to_bond(details: ContractDetails, currency: Optional[str]) -> Bond:
    contract_ = details.contract
    isin_ = next((tag_.value for tag_ in details.secIdList or [] if tag_.tag == "ISIN"), None)
    currency_ = contract_.currency or currency
    if details.maturity:
        coupon_ = Decimal(str(details.coupon))
        maturity_ = datetime.strptime(details.maturity[:8], "%Y%m%d").date()
    else:
        coupon_, maturity_ = _parse_description(details.descAppend)
    return Bond(
        contract_id=contract_.conId,
        isin=isin_,
        description=details.descAppend,
        bond_type=contract_.tradingClass,
        currency=currency_,
        annual_coupon=coupon_ / 100,  # IBKR and descAppend quote coupons in percent
        maturity=maturity_,
        issuer=details.longName or None,
        inflation_linked=details.evRule.startswith("factor"),  # index-ratio factor, e.g. DBRI
        callable=details.callable,
        minimum_size=Decimal(str(details.minSize)),
        size_increment=Decimal(str(details.sizeIncrement)),
    )


async def _get_details(ib: IB, contract_id: int) -> ContractDetails:
    details_ = await ib.reqContractDetailsAsync(Contract(conId=contract_id))
    if len(details_) != 1:
        raise LookupError(f"Expected one contract for conId {contract_id}, got {len(details_)}.")
    return details_[0]


async def scan_bonds(
        ib: IB, *,
        instrument: str,
        location: str,
        scan_code: str,
        rows: int = 50,
        **filters: Unpack[BondFilters],
) -> List[Bond]:
    subscription_ = ScannerSubscription(
        instrument=instrument,
        locationCode=location,
        scanCode=scan_code,
        numberOfRows=rows,
    )
    tags_ = [TagValue(name_, str(value_)) for name_, value_ in filters.items()]
    results_ = await ib.reqScannerDataAsync(subscription_, scannerSubscriptionFilterOptions=tags_)
    details_ = await gather(*(_get_details(ib, result_.contractDetails.contract.conId) for result_ in results_))

    bonds_: List[Bond] = []
    for item_ in details_:
        try:
            bonds_.append(_to_bond(item_, filters.get("currencyLike")))
        except ValueError:
            _logger.warning(
                f"Skipping conId {item_.contract.conId}: cannot read coupon/maturity from {item_.descAppend!r}.")
    return bonds_


def _to_quote(ticker: Optional[Ticker]) -> Optional[BondQuote]:
    if ticker is None:
        return None

    price_, live_ = ticker.marketPrice(), ticker.marketDataType == 1
    if isnan(price_) or price_ <= 0:
        price_, live_ = ticker.close, False
    if isnan(price_) or price_ <= 0:
        return None
    return BondQuote(price=Decimal(str(price_)), as_of=ticker.time or datetime.now(timezone.utc), live=live_)


async def quote_bonds(ib: IB, bonds: List[Bond]) -> List[Bond]:
    contracts_ = [Contract(conId=bond_.contract_id) for bond_ in bonds]

    await ib.qualifyContractsAsync(*contracts_)

    tickers_ = {ticker_.contract.conId: ticker_ for ticker_ in await ib.reqTickersAsync(*contracts_)}

    return [replace(bond_, quote=_to_quote(tickers_.get(bond_.contract_id))) for bond_ in bonds]
