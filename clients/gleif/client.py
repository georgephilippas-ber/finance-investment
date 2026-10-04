from typing import Optional

import requests

if __package__:
    from .domain import LegalEntity
else:
    from domain import LegalEntity

__all__ = ["get_legal_entity_by_isin"]

_BASE_URL = "https://api.gleif.org/api/v1"


def get_legal_entity_by_isin(isin: str) -> Optional[LegalEntity]:
    isin = isin.strip().upper()
    if not isin:
        raise ValueError("!ISIN")

    response = requests.get(
        f"{_BASE_URL}/lei-records",
        params={"filter[isin]": isin},
        headers={"Accept": "application/vnd.api+json"},
        timeout=30,
    )
    response.raise_for_status()
    records_ = response.json().get("data")
    if not isinstance(records_, list):
        raise ValueError()
    if not records_:
        return None
    if len(records_) != 1:
        raise LookupError(f"Multiple LEIs for ISIN {isin}.")

    attributes_ = records_[0]["attributes"]
    entity_ = attributes_["entity"]
    return LegalEntity(
        lei=attributes_["lei"],
        legal_name=entity_["legalName"]["name"],
        country=entity_["legalAddress"]["country"],
        status=entity_["status"],
    )

if __name__ == "__main__":
    print(get_legal_entity_by_isin("FR001400IB52"))