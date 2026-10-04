import json
import os
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from sqlite3 import connect, Connection
from typing import Optional, List, Dict, Set

import requests
from pandas import DataFrame, read_sql_query

from clients.common.domain import EndOfDayPrice, Provider, SecurityInformation
from settings import HTTP_TIMEOUT_SECONDS, PROJECT_ROOT

if __package__:
    from .configuration import CACHE_DIRECTORY
    from .domain import _Symbol
else:
    from configuration import CACHE_DIRECTORY
    from clients.eodhd.domain import _Symbol


_SEARCH_LIMIT = 500

def _api_key() -> str:
    key_: Optional[str] = os.getenv("EODHD_API_KEY")

    if not key_:
        raise RuntimeError("!EODHD_API_KEY")

    return key_.strip()


def _get_exchanges(load_from_cache: bool = True) -> List[Dict]:
    filename_ = CACHE_DIRECTORY / "exchanges.json"

    if load_from_cache and filename_.is_file():
        with filename_.open(encoding="utf-8") as file_:
            return json.load(file_)

    response = requests.get(
        "https://eodhd.com/api/exchanges-list/",
        params={"api_token": _api_key()},
        timeout=HTTP_TIMEOUT_SECONDS,
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


def _create_exchanges_database(load_from_cache: bool = True) -> Path:
    exchanges_ = _get_exchanges(load_from_cache=load_from_cache)
    directory_ = PROJECT_ROOT / "domain" / "exchanges"

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

    with closing[Connection](connect(filename_)) as connection_, connection_:
        connection_.execute("BEGIN")
        connection_.execute(
            """
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
    filename_ = PROJECT_ROOT / "domain" / "exchanges" / "exchanges.sqlite"
    with closing(connect(f"{filename_.as_uri()}?mode=ro", uri=True)) as connection_:
        return read_sql_query("SELECT * FROM exchanges", connection_)


def _resolve_symbol(
        ticker: str,
        *,
        operating_mic: Optional[str] = None,
        eodhd_code: Optional[str] = None,
) -> str:
    ticker = ticker.strip().upper()
    operating_mic = operating_mic.strip().upper() if operating_mic is not None else None
    eodhd_code = eodhd_code.strip().upper() if eodhd_code is not None else None

    if not ticker:
        raise ValueError("!ticker")
    if not operating_mic and not eodhd_code:
        raise ValueError("!operating_mic and !eodhd_code")

    if operating_mic:
        exchanges_ = read_exchanges_database()
        codes_ = exchanges_.loc[exchanges_["operating_mic"] == operating_mic, "eodhd_code"]
        if codes_.empty:
            raise LookupError()
        code_ = codes_.iloc[0]
        if eodhd_code and eodhd_code != code_:
            raise ValueError()

        eodhd_code = code_

    return ticker if ticker.endswith(f".{eodhd_code}") else f"{ticker}.{eodhd_code}"


def _get_symbols_by_ticker(
        ticker: str,
        *,
        operating_mic: Optional[str] = None,
        eodhd_code: Optional[str] = None,
) -> List[_Symbol]:
    symbol_ = _resolve_symbol(ticker, operating_mic=operating_mic, eodhd_code=eodhd_code)
    ticker_, _, exchange_ = symbol_.rpartition(".")

    response = requests.get(
        f"https://eodhd.com/api/exchange-symbol-list/{exchange_}",
        params={"symbols": ticker_, "fmt": "json", "api_token": _api_key()},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    records_ = response.json()
    if not isinstance(records_, list) or not all(isinstance(record_, dict) for record_ in records_):
        raise ValueError()
    return [
        _Symbol(
            code=record_["Code"],
            name=record_["Name"],
            country=record_["Country"],
            exchange=record_["Exchange"],
            currency=record_["Currency"],
            type=record_["Type"],
            isin=record_.get("Isin"),
        )
        for record_ in records_
    ]


def _get_symbols_by_isin(isin: str, *, currency: str) -> List[_Symbol]:
    isin = isin.strip().upper()
    currency = currency.strip().upper()
    if not isin or not currency:
        raise ValueError("!ISIN and !currency")

    response = requests.get(
        f"https://eodhd.com/api/search/{isin}",
        params={"limit": _SEARCH_LIMIT, "fmt": "json", "api_token": _api_key()},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    records_ = response.json()
    if not isinstance(records_, list) or not all(isinstance(record_, dict) for record_ in records_):
        raise ValueError()
    if len(records_) == _SEARCH_LIMIT:
        raise LookupError("> limit")

    return [
        _Symbol(
            code=record_["Code"],
            name=record_["Name"],
            country=record_["Country"],
            exchange=record_["Exchange"],
            currency=record_["Currency"],
            type=record_["Type"],
            isin=record_["ISIN"],
        )
        for record_ in records_
        if record_.get("ISIN") == isin and record_.get("Currency") == currency
    ]


def _get_symbols_in_exchange(exchange: str, load_from_cache: bool = True) -> List[_Symbol]:
    exchange = exchange.strip().upper()

    if not exchange:
        raise ValueError()

    exchanges_ = read_exchanges_database()
    matches_ = exchanges_.loc[exchanges_["operating_mic"].str.upper() == exchange]
    if matches_.empty:
        matches_ = exchanges_.loc[exchanges_["eodhd_code"].str.upper() == exchange]
    if matches_.empty:
        raise LookupError()

    codes_ = matches_["eodhd_code"].unique()
    if len(codes_) != 1:
        raise ValueError()

    eodhd_code = codes_[0]
    filename_ = CACHE_DIRECTORY / f"symbols_{eodhd_code}.json"
    if load_from_cache and filename_.is_file():
        with filename_.open(encoding="utf-8") as file_:
            records_ = json.load(file_)
    else:
        response = requests.get(
            f"https://eodhd.com/api/exchange-symbol-list/{eodhd_code}",
            params={"fmt": "json", "api_token": _api_key()},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        records_ = response.json()

    if not isinstance(records_, list) or not all(isinstance(record_, dict) for record_ in records_):
        raise ValueError()

    symbols_ = [
        _Symbol(
            code=record_["Code"],
            name=record_["Name"],
            country=record_["Country"],
            exchange=record_["Exchange"],
            currency=record_["Currency"],
            type=record_["Type"],
            isin=record_.get("Isin"),
        )
        for record_ in records_
    ]

    if not load_from_cache or not filename_.is_file():
        CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        with filename_.open("w", encoding="utf-8") as file_:
            json.dump(records_, file_, indent=2)
            file_.write("\n")

    return symbols_


def get_latest_price(security: SecurityInformation, *, lookback_days: int = 14) -> EndOfDayPrice:
    if security.provider is not Provider.EODHD:
        raise ValueError()

    response = requests.get(
        f"https://eodhd.com/api/eod/{security.symbol}.{security.exchange}",
        params={
            "from": (date.today() - timedelta(days=lookback_days)).isoformat(),
            "fmt": "json",
            "api_token": _api_key(),
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    records_ = response.json()
    if not isinstance(records_, list) or not all(isinstance(record_, dict) for record_ in records_):
        raise ValueError()
    if not records_:
        raise LookupError()

    record_ = max(records_, key=lambda record_: record_["date"])
    return EndOfDayPrice(
        date=record_["date"],
        open=record_["open"],
        high=record_["high"],
        low=record_["low"],
        close=record_["close"],
        adjusted_close=record_["adjusted_close"],
        volume=record_["volume"],
    )


def _symbol_to_security_information(symbol: _Symbol, eodhd_codes: Set[str]) -> Optional[SecurityInformation]:
    if symbol.exchange in eodhd_codes:
        exchange_ = symbol.exchange
    elif symbol.country == "USA":
        exchange_ = "US"
    else:
        return None

    return SecurityInformation(
        provider=Provider.EODHD,
        symbol=symbol.code,
        exchange=exchange_,
        currency=symbol.currency,
        isin=symbol.isin or None,
    )


def _symbols_to_security_information(symbols: List[_Symbol]) -> List[SecurityInformation]:
    codes_ = set(read_exchanges_database()["eodhd_code"])
    return [
        security_ for security_ in (_symbol_to_security_information(symbol_, codes_) for symbol_ in symbols)
        if security_ is not None
    ]


def get_security_information_by_ticker(
        ticker: str,
        *,
        operating_mic: Optional[str] = None,
        eodhd_code: Optional[str] = None,
) -> List[SecurityInformation]:
    return _symbols_to_security_information(
        _get_symbols_by_ticker(ticker, operating_mic=operating_mic, eodhd_code=eodhd_code)
    )


def get_security_information_by_isin(isin: str, *, currency: str) -> List[SecurityInformation]:
    return _symbols_to_security_information(_get_symbols_by_isin(isin, currency=currency))


def get_security_information_in_exchange(exchange: str, load_from_cache: bool = True) -> List[SecurityInformation]:
    return _symbols_to_security_information(_get_symbols_in_exchange(exchange, load_from_cache=load_from_cache))


if __name__ == "__main__":
    pass
