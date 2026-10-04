from pathlib import Path

__all__ = ["HTTP_TIMEOUT_SECONDS", "MONTHS_PER_YEAR", "PROJECT_ROOT"]

PROJECT_ROOT: Path = Path(__file__).resolve().parent
HTTP_TIMEOUT_SECONDS: float = 30
MONTHS_PER_YEAR: int = 12
