import json
from asyncio import wait_for
from pathlib import Path
from typing import Dict, List

from ib_async import IB, Contract
from pandas import DataFrame

from clients.common.domain import Provider, SecurityInformation
from clients.common.printing import print_table
from clients.eodhd.client import get_security_information_by_isin, read_exchanges_database

__all__ = ["SecurityInformationMapping", "get_augmented_exchanges_database", "print_augmented_exchanges_database"]

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


def get_augmented_exchanges_database() -> DataFrame:
    return _augmented_exchanges_database_ibkr(read_exchanges_database())


def print_augmented_exchanges_database(exchanges: DataFrame) -> None:
    headers_: List[str] = ["Operating MIC", "EODHD code", "IBKR exchange", "IBKR other exchanges", "Country",
                           "Currency", "Name"]
    rows_: List[List[str]] = [
        [
            row_.operating_mic,
            row_.eodhd_code,
            row_.ibkr_exchange,
            ", ".join(row_.ibkr_other_exchanges),
            row_.country,
            row_.currency,
            row_.name,
        ]
        for row_ in exchanges.sort_values(["country", "operating_mic"]).itertuples(index=False)
    ]
    print_table(headers_, rows_, first_right_aligned_column=len(headers_))
    covered_ = sum(1 for row_ in rows_ if row_[2])
    print(f"({len(rows_)} {'row' if len(rows_) == 1 else 'rows'}, {covered_} with IBKR)")


class SecurityInformationMapping:
    @staticmethod
    def from_ibkr_to_eodhd(security: SecurityInformation) -> SecurityInformation:
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

        tickers_ = {
            listing_.symbol for listing_ in get_security_information_by_isin(security.isin, currency=security.currency)
            if listing_.exchange == eodhd_code_
        }
        if len(tickers_) != 1:
            raise LookupError()

        return SecurityInformation(
            provider=Provider.EODHD,
            symbol=next(iter(tickers_)),
            exchange=eodhd_code_,
            isin=security.isin,
            currency=security.currency,
        )

    @staticmethod
    async def from_eodhd_to_ibkr(
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
