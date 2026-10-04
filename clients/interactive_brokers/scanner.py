from typing import List, Any, TypedDict, Unpack

from ib_async import IB, ScanData, ScannerSubscription, TagValue

__all__ = ["scan_bonds"]


class BondFilters(TypedDict, total=False):
    maturityDateAbove: str  # YYYYMMDD
    maturityDateBelow: str  # YYYYMMDD
    bondVarCouponRateIs: Any


async def scan_bonds(
        ib: IB, *,
        instrument: str,
        location: str,
        scan_code: str,
        rows: int = 50,
        **filters: Unpack[BondFilters],
) -> List[ScanData]:
    subscription_ = ScannerSubscription(
        instrument=instrument,
        locationCode=location,
        scanCode=scan_code,
        numberOfRows=rows,
    )
    tags_ = [TagValue(name_, str(value_)) for name_, value_ in filters.items()]
    return await ib.reqScannerDataAsync(subscription_, scannerSubscriptionFilterOptions=tags_)
