import re
from typing import Optional, Set

import requests

from settings import HTTP_TIMEOUT_SECONDS

if __package__:
    from .domain import LegalEntity
else:
    from domain import LegalEntity

__all__ = ["get_legal_entity_by_isin"]

_FIRDS_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"
_GLEIF_URL = "https://api.gleif.org/api/v1"
_GLEIF_HEADERS = {"Accept": "application/vnd.api+json"}
_ISIN_PATTERN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]")
_FIRDS_MAX_RECORDS = 500


def _get_lei_from_firds(isin: str) -> Optional[str]:
    response = requests.get(
        _FIRDS_URL,
        params={"q": f"isin:{isin}", "fl": "lei", "rows": _FIRDS_MAX_RECORDS, "wt": "json"},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    records_ = response.json().get("response", {}).get("docs")
    if not isinstance(records_, list):
        raise ValueError()

    leis_: Set[str] = {record_["lei"] for record_ in records_ if record_.get("lei")}
    if len(leis_) > 1:
        raise LookupError()
    return next(iter(leis_), None)


def _get_lei_from_gleif(isin: str) -> Optional[str]:
    response = requests.get(f"{_GLEIF_URL}/lei-records", params={"filter[isin]": isin}, headers=_GLEIF_HEADERS,
                            timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    records_ = response.json().get("data")
    if not isinstance(records_, list):
        raise ValueError()
    if len(records_) > 1:
        raise LookupError()
    return records_[0]["attributes"]["lei"] if records_ else None


def _get_legal_entity_by_lei(lei: str) -> LegalEntity:
    response = requests.get(f"{_GLEIF_URL}/lei-records/{lei}", headers=_GLEIF_HEADERS, timeout=HTTP_TIMEOUT_SECONDS)
    response.raise_for_status()
    attributes_ = response.json()["data"]["attributes"]
    entity_ = attributes_["entity"]
    return LegalEntity(
        lei=attributes_["lei"],
        legal_name=entity_["legalName"]["name"],
        country=entity_["legalAddress"]["country"],
        status=entity_["status"],
    )


def get_legal_entity_by_isin(isin: str) -> Optional[LegalEntity]:
    isin = isin.strip().upper()
    if not _ISIN_PATTERN.fullmatch(isin):
        raise ValueError()

    lei_ = _get_lei_from_firds(isin) or _get_lei_from_gleif(isin)
    return _get_legal_entity_by_lei(lei_) if lei_ is not None else None


if __name__ == "__main__":
    print(get_legal_entity_by_isin("FR001400IB52"))
