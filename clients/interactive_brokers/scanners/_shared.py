from asyncio import Semaphore, gather, to_thread
from datetime import datetime, timezone
from decimal import Decimal
from logging import getLogger
from math import isnan
from typing import Dict, List, Optional, Tuple

from ib_async import IB, Contract, ContractDetails, ScannerSubscription, TagValue, Ticker
from requests import RequestException

from clients.lei_resolver.client import get_legal_entity_by_isin
from clients.lei_resolver.domain import LegalEntity

_logger = getLogger(__name__)

_LEI_CONCURRENCY = 4

_DELAYED_FROZEN = 4


async def scan_details(client: IB, instrument: str, location: str, scan_code: str, rows: int,
                       filters: Dict[str, object]) -> List[ContractDetails]:
    subscription_ = ScannerSubscription(instrument=instrument, locationCode=location, scanCode=scan_code,
                                        numberOfRows=rows)
    tags_ = [TagValue(name_, str(value_)) for name_, value_ in filters.items()]
    results_ = await client.reqScannerDataAsync(subscription_, scannerSubscriptionFilterOptions=tags_)
    return list(await gather(*(_get_details(client, result_.contractDetails.contract.conId) for result_ in results_)))


async def _get_details(client: IB, contract_id: int) -> ContractDetails:
    details_ = await client.reqContractDetailsAsync(Contract(conId=contract_id))
    if len(details_) != 1:
        raise LookupError()
    return details_[0]


def get_isin(details: ContractDetails) -> Optional[str]:
    return next((tag_.value for tag_ in details.secIdList or [] if tag_.tag == "ISIN"), None)


async def resolve_legal_entities(isins: List[Optional[str]]) -> List[Optional[LegalEntity]]:
    semaphore_ = Semaphore(_LEI_CONCURRENCY)

    async def _resolve(isin: Optional[str]) -> Optional[LegalEntity]:
        if isin is None:
            return None
        async with semaphore_:
            try:
                return await to_thread(get_legal_entity_by_isin, isin)
            except (RequestException, LookupError, ValueError) as error_:
                _logger.warning(f"No legal entity for ISIN {isin}: {error_}")
                return None

    return list(await gather(*(_resolve(isin_) for isin_ in isins)))


async def get_market_prices(client: IB, contract_ids: List[int]) -> Dict[int, Tuple[Decimal, datetime, bool]]:
    contracts_ = [Contract(conId=contract_id_) for contract_id_ in contract_ids]
    await client.qualifyContractsAsync(*contracts_)
    client.reqMarketDataType(_DELAYED_FROZEN)
    prices_: Dict[int, Tuple[Decimal, datetime, bool]] = {}
    for ticker_ in await client.reqTickersAsync(*contracts_):
        price_ = _market_price(ticker_)
        if price_ is not None:
            prices_[ticker_.contract.conId] = price_
    return prices_


def _market_price(ticker: Ticker) -> Optional[Tuple[Decimal, datetime, bool]]:
    price_, live_ = ticker.marketPrice(), ticker.marketDataType == 1
    if isnan(price_) or price_ <= 0:
        price_, live_ = ticker.close, False
    if isnan(price_) or price_ <= 0:
        return None
    return Decimal(str(price_)), ticker.time or datetime.now(timezone.utc), live_
