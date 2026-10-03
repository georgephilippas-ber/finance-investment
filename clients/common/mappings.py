import json
from asyncio import wait_for
from pathlib import Path
from typing import Dict, List

from ib_async import IB, Contract
from pandas import DataFrame

from clients.common.domain import Provider, SecurityInformation
from clients.eodhd.client import get_symbols_by_isin, read_exchanges_database

__all__ = ["eodhd_to_ibkr_security_information", "ibkr_to_eodhd_security_information"]

IBKR_MAPPING_FILE: Path = Path(__file__).resolve().parents[
                              2] / "domain" / "exchanges" / "ibkr_operating_mic_mapping.json"


def _augmented_exchanges_database_ibkr(exchanges: DataFrame) -> DataFrame:
    with IBKR_MAPPING_FILE.open(encoding="utf-8") as file_:
        mapping_: Dict[str, List[str]] = json.load(file_)

    unknown_mics_ = set(mapping_) - set(exchanges["operating_mic"])
    if unknown_mics_:
        raise ValueError()

    codes_ = exchanges["operating_mic"].map(lambda mic_: mapping_.get(mic_, []))
    return exchanges.assign(
        ibkr_exchange=codes_.map(lambda codes: codes[0] if codes else ""),
        ibkr_other_exchanges=codes_.map(lambda codes: tuple(codes[1:])),
    )


def ibkr_to_eodhd_security_information(security: SecurityInformation) -> SecurityInformation:
    if security.provider is not Provider.IBKR or not security.isin:
        raise ValueError()

    exchanges_ = _augmented_exchanges_database_ibkr(read_exchanges_database())
    matches_ = exchanges_.loc[
        (exchanges_["ibkr_exchange"] == security.exchange)
        | exchanges_["ibkr_other_exchanges"].map(lambda codes: security.exchange in codes)
        ]
    eodhd_codes_ = set(matches_["eodhd_code"])
    if len(eodhd_codes_) != 1:
        raise LookupError()
    eodhd_code_ = next(iter(eodhd_codes_))

    symbols_ = [
        symbol_ for symbol_ in get_symbols_by_isin(security.isin, currency=security.currency)
        if symbol_.exchange == eodhd_code_
    ]
    tickers_ = {symbol_.code for symbol_ in symbols_}
    if len(tickers_) != 1:
        raise LookupError()

    return SecurityInformation(
        provider=Provider.EODHD,
        symbol=next(iter(tickers_)),
        exchange=eodhd_code_,
        isin=security.isin,
        currency=security.currency,
    )


async def eodhd_to_ibkr_security_information(
        ib: IB,
        security: SecurityInformation,
        *,
        timeout: float = 50,
) -> SecurityInformation:
    if security.provider is not Provider.EODHD or not security.isin:
        raise ValueError()

    exchanges_ = _augmented_exchanges_database_ibkr(read_exchanges_database())
    matches_ = exchanges_.loc[exchanges_["eodhd_code"] == security.exchange]
    ibkr_codes_ = {code_ for code_ in matches_["ibkr_exchange"] if code_} | {
        code_ for codes_ in matches_["ibkr_other_exchanges"] for code_ in codes_
    }
    if not ibkr_codes_:
        raise LookupError()

    details_ = await wait_for(
        ib.reqContractDetailsAsync(Contract(secType="STK", secIdType="ISIN", secId=security.isin)),
        timeout=timeout,
    )
    contracts_ = {
        detail_.contract.conId: detail_.contract
        for detail_ in details_
        if detail_.contract.currency == security.currency and detail_.contract.primaryExchange in ibkr_codes_
    }
    if len(contracts_) != 1:
        raise LookupError()
    contract_ = next(iter(contracts_.values()))

    return SecurityInformation(
        provider=Provider.IBKR,
        symbol=contract_.symbol,
        exchange=contract_.primaryExchange,
        currency=security.currency,
        isin=security.isin,
        contract_id=contract_.conId,
    )
