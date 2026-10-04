# LEI resolver

`clients/lei_resolver/client.py` — finds the legal entity that issued a security, from public registers. No API key or
account is needed.

## `get_legal_entity_by_isin`
```python
def get_legal_entity_by_isin(isin: str) -> Optional[LegalEntity]
```
The issuer of the security with this ISIN, as a [`LegalEntity`](#legalentity). Two steps:

1. **ISIN → issuer LEI**
   - First [ESMA FIRDS](https://registers.esma.europa.eu), the EU register of instruments admitted to trading on EU
     venues. It covers international `XS…` Eurobonds, which GLEIF's ISIN mapping mostly lacks.
   - If FIRDS has no record, GLEIF's ISIN-to-LEI mapping, for securities not traded in the EU.
2. **LEI → entity details** from [GLEIF](https://www.gleif.org): legal name, country, status.

That is two or three requests per call. Returns `None` when neither register knows the ISIN. In a live scan of 50 EUR
investment-grade corporate bonds, all 50 resolved; GLEIF alone had resolved 16.

The entity is the **legal issuer**, which is often a financing subsidiary rather than the group: Grenke bonds resolve
to Grenke Finance PLC, DXC bonds to DXC Capital Funding DAC, and an `ACAFP` bond to Crédit Agricole Assurances.

**Errors.** `ValueError` for a string that is not shaped like an ISIN or an unexpected response; `LookupError` if a
register returns several different LEIs for the ISIN. HTTP errors and timeouts (30 seconds per request) propagate.
GLEIF limits request frequency, so cache results when resolving many ISINs.

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
