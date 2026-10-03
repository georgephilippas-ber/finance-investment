import sys
from asyncio import run
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from clients.common.exchanges import get_augmented_exchanges_database, print_augmented_exchanges_database
from clients.common.mappings import SecurityInformationMapping
from clients.eodhd.client import get_security_information_by_isin, get_security_information_by_ticker, get_latest_price
from clients.interactive_brokers.client import (connect, disconnect, get_positions_as_security_information,
                                                print_full_account_information)
from printing import print_section, print_subsection

__all__ = ["features"]


def _exchanges() -> None:
    print_section("Exchanges")
    print_subsection("database with IBKR codes")
    print_augmented_exchanges_database(get_augmented_exchanges_database())


def _eodhd_lookup() -> None:
    print_section("EODHD")
    print_subsection("lookup by ticker")
    apple_ = get_security_information_by_ticker("AAPL", eodhd_code="US")[0]
    print(apple_)

    print_subsection("lookup by ISIN (all EUR listings)")
    for listing_ in get_security_information_by_isin("DE0007164600", currency="EUR"):
        print(f"{listing_.symbol}.{listing_.exchange}")

    print_subsection("latest end-of-day price")
    print(get_latest_price(apple_))


async def _ibkr() -> None:
    print_section("Interactive Brokers")
    try:
        ib = await connect()
    except (ConnectionError, OSError, TimeoutError):
        print("IB Gateway / TWS is not reachable; skipping the IBKR part.")
        return

    try:
        print_subsection("positions → EODHD → latest close")
        for security_ in await get_positions_as_security_information(ib):
            eodhd_ = SecurityInformationMapping.from_ibkr_to_eodhd(security_)
            print(f"{security_.symbol}.{security_.exchange} (IBKR) → {eodhd_.symbol}.{eodhd_.exchange} (EODHD), "
                  f"ISIN {security_.isin}, close {get_latest_price(eodhd_).close}")

        print_subsection("EODHD → IBKR")
        for isin_, currency_ in (("US0378331005", "USD"), ("DE0007664039", "EUR")):
            eodhd_ = get_security_information_by_isin(isin_, currency=currency_)[0]
            ibkr_ = await SecurityInformationMapping.from_eodhd_to_ibkr(ib, eodhd_)
            print(f"{eodhd_.symbol}.{eodhd_.exchange} (EODHD) → {ibkr_.symbol} on {ibkr_.exchange}, "
                  f"contract {ibkr_.contract_id} (IBKR)")

        print_subsection("account summary and positions")
        await print_full_account_information(ib)
    finally:
        disconnect(ib)


async def features() -> None:
    load_dotenv(ROOT / ".env")
    _exchanges()
    _eodhd_lookup()
    await _ibkr()


if __name__ == "__main__":
    run(features())
