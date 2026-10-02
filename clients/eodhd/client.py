import json
import os
from contextlib import closing
from pathlib import Path
from sqlite3 import connect
from typing import Optional, List, Dict

import requests
from dotenv import load_dotenv
from pandas import DataFrame, read_sql_query

if __package__:
    from .configuration import CACHE_DIRECTORY
    from .domain import IdentifierMapping
else:
    from configuration import CACHE_DIRECTORY
    from domain import IdentifierMapping


def api_key() -> str:
    key_: Optional[str] = os.getenv("EODHD_API_KEY")

    if not key_:
        raise RuntimeError("EODHD_API_KEY must be set in the environment or project .env file.")

    return key_.strip()


def get_exchanges(load_from_cache: bool = True) -> List[Dict]:
    filename_ = CACHE_DIRECTORY / "exchanges.json"

    if load_from_cache and filename_.is_file():
        with filename_.open(encoding="utf-8") as file_:
            return json.load(file_)

    response = requests.get(
        "https://eodhd.com/api/exchanges-list/",
        params={"api_token": api_key()},
        timeout=30,
    )

    response.raise_for_status()
    response_ = response.json()

    if not isinstance(response_, list) or not all(isinstance(exchange, dict) for exchange in response_):
        raise ValueError("EODHD returned an invalid exchange list.")

    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with filename_.open("w", encoding="utf-8") as file_:
        json.dump(response_, file_, indent=2)
        file_.write("\n")

    return response_


def create_exchanges_database(load_from_cache: bool = True) -> Path:
    exchanges_ = get_exchanges(load_from_cache=load_from_cache)
    directory_ = Path(__file__).resolve().parents[2] / "domain" / "exchanges"

    with (directory_ / "us_operating_mic_mapping.json").open(encoding="utf-8") as file_:
        us_mapping_ = json.load(file_)

    rows_ = [
        (mic_, details_["Name"].strip(), details_["Country"].strip(), details_["Currency"].strip(), "US")
        for mic_, details_ in us_mapping_.items()
    ]

    for exchange_ in exchanges_:
        if exchange_["Code"] == "US":
            continue

        operating_mics_ = (
            "FIXED_INCOME" if exchange_["Code"] == "GBOND"
            else exchange_.get("OperatingMIC")
        )
        if not operating_mics_:
            continue

        for mic_ in operating_mics_.split(","):
            mic_ = mic_.strip()
            if mic_:
                rows_.append((
                    mic_,
                    exchange_["Name"].strip(),
                    exchange_["Country"].strip(),
                    exchange_["Currency"].strip(),
                    exchange_["Code"].strip(),
                ))

    directory_.mkdir(parents=True, exist_ok=True)
    filename_ = directory_ / "exchanges.sqlite"

    with closing(connect(filename_)) as connection_, connection_:
        connection_.execute("BEGIN")
        connection_.execute("""
            CREATE TABLE IF NOT EXISTS exchanges (
                operating_mic TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                currency TEXT NOT NULL,
                eodhd_code TEXT NOT NULL
            )
        """)
        columns_ = {column_[1] for column_ in connection_.execute("PRAGMA table_info(exchanges)")}
        if "eodhd_code" not in columns_:
            connection_.execute(
                "ALTER TABLE exchanges ADD COLUMN eodhd_code TEXT NOT NULL DEFAULT ''"
            )

        connection_.execute("DELETE FROM exchanges")
        connection_.executemany(
            "INSERT INTO exchanges (operating_mic, name, country, currency, eodhd_code) VALUES (?, ?, ?, ?, ?)",
            rows_,
        )

    return filename_


def read_exchanges_database() -> DataFrame:
    filename_ = Path(__file__).resolve().parents[2] / "domain" / "exchanges" / "exchanges.sqlite"
    with closing(connect(f"{filename_.as_uri()}?mode=ro", uri=True)) as connection_:
        return read_sql_query("SELECT * FROM exchanges", connection_)


def get_identifier_mapping(
        ticker: str,
        *,
        operating_mic: Optional[str] = None,
        eodhd_code: Optional[str] = None,
) -> IdentifierMapping:
    ticker = ticker.strip().upper()
    eodhd_code = eodhd_code.strip().upper() if eodhd_code is not None else None
    operating_mic = operating_mic.strip().upper() if operating_mic is not None else None

    if not ticker:
        raise ValueError("ticker must not be blank.")
    if not operating_mic and not eodhd_code:
        raise ValueError("Provide operating_mic or eodhd_code.")

    if operating_mic:
        exchanges_ = read_exchanges_database()
        matches_ = exchanges_.loc[exchanges_["operating_mic"] == operating_mic, "eodhd_code"]
        if matches_.empty:
            raise LookupError(f"Unknown OperatingMIC: {operating_mic}")
        code_ = matches_.iloc[0]
        if eodhd_code and eodhd_code != code_:
            raise ValueError("operating_mic and eodhd_code refer to different EODHD exchanges.")
        eodhd_code = code_

    symbol_ = ticker if ticker.endswith(f".{eodhd_code}") else f"{ticker}.{eodhd_code}"
    response = requests.get(
        "https://eodhd.com/api/id-mapping",
        params={"filter[symbol]": symbol_, "fmt": "json", "api_token": api_key()},
        timeout=30,
    )
    response.raise_for_status()
    response_ = response.json()
    records_ = response_.get("data") if isinstance(response_, dict) else None
    if not isinstance(records_, list) or not all(
            isinstance(record_, dict) and isinstance(record_.get("symbol"), str)
            for record_ in records_
    ):
        raise ValueError("EODHD returned an invalid identifier mapping response.")

    matches_ = [record_ for record_ in records_ if record_["symbol"].upper() == symbol_]
    if not matches_:
        raise LookupError(f"No identifier mapping found for {symbol_}.")
    if len(matches_) != 1:
        raise LookupError(f"Multiple identifier mappings found for {symbol_}.")

    record_ = matches_[0]
    for field_ in ("isin", "figi", "lei", "cusip", "cik"):
        value_ = record_.get(field_)
        if value_ is not None and not isinstance(value_, str):
            raise ValueError(f"EODHD returned an invalid {field_} for {symbol_}.")

    return IdentifierMapping(
        symbol=record_["symbol"],
        isin=record_.get("isin"),
        figi=record_.get("figi"),
        lei=record_.get("lei"),
        cusip=record_.get("cusip"),
        cik=record_.get("cik"),
    )


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    # print(api_key())
    # create_exchanges_database()

    print(get_identifier_mapping("AAPL", operating_mic="XNAS"))
