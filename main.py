from asyncio import run
from pprint import pprint

from dotenv import load_dotenv

from clients.common.mappings import ibkr_to_eodhd_security_information
from clients.eodhd.client import get_symbols_by_ticker, get_symbols_by_isin
from clients.interactive_brokers.client import (connect, disconnect, get_account_information, get_positions,
                                                print_positions, to_security_information)


async def _ibkr_main() -> None:
    ib = await connect()
    try:
        # pprint(await get_account_information(ib))
        positions_ = get_positions(ib)
        # print_positions(positions_)
        for position_ in positions_:
            security_ = await to_security_information(ib, position_)
            pprint(security_)
            print()
            pprint(ibkr_to_eodhd_security_information(security_))
            print()
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()

    run(_ibkr_main())
