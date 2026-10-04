from dataclasses import dataclass

__all__ = ["LegalEntity"]


@dataclass(frozen=True)
class LegalEntity:
    lei: str
    legal_name: str
    country: str
    status: str
