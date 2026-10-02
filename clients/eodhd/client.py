import json
import os
from contextlib import closing
from pathlib import Path
from typing import Optional, List, Dict

import pandas as pd
import requests

from sqlite3 import connect

from dotenv import load_dotenv

if __package__:
    from .configuration import CACHE_DIRECTORY
else:
    from configuration import CACHE_DIRECTORY


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


def read_exchanges_database() -> pd.DataFrame:
    filename_ = Path(__file__).resolve().parents[2] / "domain" / "exchanges" / "exchanges.sqlite"
    with closing(connect(f"{filename_.as_uri()}?mode=ro", uri=True)) as connection_:
        return pd.read_sql_query("SELECT * FROM exchanges", connection_)


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    print(api_key())
    create_exchanges_database()
    print(read_exchanges_database())
