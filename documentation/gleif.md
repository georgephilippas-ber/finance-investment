# GLEIF client

`clients/gleif/client.py` — looks up legal entities in the public [GLEIF](https://www.gleif.org) database of Legal
Entity Identifiers (LEIs). No API key or account is needed.

## `get_legal_entity_by_isin`
```python
def get_legal_entity_by_isin(isin: str) -> Optional[LegalEntity]
```
The issuer of the security with this ISIN, as a [`LegalEntity`](#legalentity), from GLEIF's ISIN-to-LEI mapping.
One request per call (`GET https://api.gleif.org/api/v1/lei-records?filter[isin]=…`).
- Returns `None` when GLEIF has no mapping for the ISIN. Coverage is very good for recent European issues and
  patchier elsewhere (no record was found for the Volkswagen bond XS2617457127, for example).
- The entity is the **legal issuer**, which can be a subsidiary: the Crédit Agricole bond FR0013523602 maps to
  Crédit Agricole Assurances, not Crédit Agricole S.A.
- Raises `ValueError` for an empty ISIN or an unexpected response, `LookupError` if several LEIs match. HTTP errors
  and timeouts (30 seconds) propagate.

GLEIF limits request frequency, so cache results when looking up many ISINs.

## `LegalEntity`
```python
@dataclass(frozen=True)
class LegalEntity:
    lei: str
    legal_name: str
    country: str
    status: str
```
- `lei` — the 20-character Legal Entity Identifier.
- `legal_name` — the registered name (`DEUTSCHE PFANDBRIEFBANK AG`).
- `country` — ISO 3166 code of the legal address.
- `status` — `ACTIVE` or `INACTIVE`.
