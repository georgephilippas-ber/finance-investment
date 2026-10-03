import sys
from asyncio import run
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from clients.common.mappings import (SecurityInformationMapping, get_augmented_exchanges_database,
                                     print_augmented_exchanges_database)
from clients.eodhd.client import get_security_information_by_isin, get_security_information_by_ticker, latest_price
from clients.interactive_brokers.client import (connect, disconnect, get_positions_as_security_information,
                                                print_full_account_information)


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _exchanges() -> None:
    _section("Exchanges database with IBKR codes")
    print_augmented_exchanges_database(get_augmented_exchanges_database())


def _eodhd_lookup() -> None:
    _section("EODHD lookup by ticker")
    apple_ = get_security_information_by_ticker("AAPL", eodhd_code="US")[0]
    print(apple_)

    _section("EODHD lookup by ISIN (all EUR listings)")
    for listing_ in get_security_information_by_isin("DE000A0F5UJ7", currency="EUR"):
        print(f"{listing_.symbol}.{listing_.exchange}")

    _section("Latest end-of-day price")
    print(latest_price(apple_))


async def _ibkr() -> None:
    try:
        ib = await connect()
    except (ConnectionError, OSError, TimeoutError):
        _section("Interactive Brokers")
        print("IB Gateway / TWS is not reachable; skipping the IBKR part.")
        return

    try:
        _section("Account and positions")
        await print_full_account_information(ib)

        _section("Positions → EODHD → latest close")
        for security_ in await get_positions_as_security_information(ib):
            eodhd_ = SecurityInformationMapping.from_ibkr_to_eodhd(security_)
            print(f"{security_.symbol}.{security_.exchange} (IBKR) → {eodhd_.symbol}.{eodhd_.exchange} (EODHD), "
                  f"ISIN {security_.isin}, close {latest_price(eodhd_).close}")

        _section("EODHD → IBKR")
        for isin_, currency_ in (("US0378331005", "USD"), ("DE0007164600", "EUR")):
            eodhd_ = get_security_information_by_isin(isin_, currency=currency_)[0]
            ibkr_ = await SecurityInformationMapping.from_eodhd_to_ibkr(ib, eodhd_)
            print(f"{eodhd_.symbol}.{eodhd_.exchange} (EODHD) → {ibkr_.symbol} on {ibkr_.exchange}, "
                  f"contract {ibkr_.contract_id} (IBKR)")
    finally:
        disconnect(ib)


async def _main() -> None:
    load_dotenv(ROOT / ".env")
    _exchanges()
    _eodhd_lookup()
    await _ibkr()


if __name__ == "__main__":
    run(_main())
