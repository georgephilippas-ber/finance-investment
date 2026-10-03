import json
from pathlib import Path
from typing import Dict, List

from pandas import DataFrame

from clients.eodhd.client import get_symbols_by_isin, read_exchanges_database

from clients.eodhd.domain import SecurityInformation as EODHDSecurityInformation
from clients.interactive_brokers.domain import SecurityInformation as IBKRSecurityInformation

__all__ = ["augmented_exchanges_database_ibkr", "ibkr_to_eodhd_security_information"]

IBKR_MAPPING_FILE: Path = Path(__file__).resolve().parents[
                              2] / "domain" / "exchanges" / "ibkr_operating_mic_mapping.json"


def augmented_exchanges_database_ibkr(exchanges: DataFrame) -> DataFrame:
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


def ibkr_to_eodhd_security_information(security: IBKRSecurityInformation) -> EODHDSecurityInformation:
    if not security.isin:
        raise ValueError()

    exchanges_ = augmented_exchanges_database_ibkr(read_exchanges_database())
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

    return EODHDSecurityInformation(
        ticker=next(iter(tickers_)),
        exchange=eodhd_code_,
        isin=security.isin,
        currency=security.currency,
    )
