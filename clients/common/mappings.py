import json
from pathlib import Path
from typing import Dict, List

from pandas import DataFrame

__all__ = ["augmented_exchanges_database_ibkr"]

IBKR_MAPPING_FILE: Path = Path(__file__).resolve().parents[2] / "domain" / "exchanges" / "ibkr_operating_mic_mapping.json"


def augmented_exchanges_database_ibkr(exchanges: DataFrame) -> DataFrame:
    with IBKR_MAPPING_FILE.open(encoding="utf-8") as file_:
        mapping_: Dict[str, List[str]] = json.load(file_)

    unknown_mics_ = set(mapping_) - set(exchanges["operating_mic"])
    if unknown_mics_:
        raise ValueError(f"IBKR mapping has unknown operating MICs: {sorted(unknown_mics_)}")

    codes_ = exchanges["operating_mic"].map(lambda mic_: mapping_.get(mic_, []))
    return exchanges.assign(
        ibkr_exchange=codes_.map(lambda codes: codes[0] if codes else ""),
        ibkr_other_exchanges=codes_.map(lambda codes: tuple(codes[1:])),
    )


if __name__ == "__main__":
    from clients.eodhd.client import read_exchanges_database

    print(augmented_exchanges_database_ibkr(read_exchanges_database()))
