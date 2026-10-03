import os
from base64 import urlsafe_b64decode

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 4001
DEFAULT_CLIENT_ID: int = 1


def host() -> str:
    return os.getenv("IBKR_HOST", DEFAULT_HOST).strip()


def port() -> int:
    return int(os.getenv("IBKR_PORT", DEFAULT_PORT))


def client_id() -> int:
    return int(os.getenv("IBKR_CLIENT_ID", DEFAULT_CLIENT_ID))


def position_tracker_key() -> bytes:
    key_ = os.getenv("IBKR_POSITION_TRACKER_KEY")
    if not key_:
        raise RuntimeError()
    return urlsafe_b64decode(key_.strip())
