import json
from pathlib import Path
from typing import Dict, List

from pandas import DataFrame

from clients.eodhd.client import read_exchanges_database
from printing import print_table

__all__ = ["get_augmented_exchanges_database", "print_augmented_exchanges_database"]

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
