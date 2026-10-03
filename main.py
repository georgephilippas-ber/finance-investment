from asyncio import run
from pprint import pprint

from dotenv import load_dotenv

from clients.common.mappings import ibkr_to_eodhd_security_information
from clients.eodhd.client import get_last_candle
from clients.interactive_brokers.client import (connect, disconnect, get_positions,
                                                to_security_information, print_positions)


async def _ibkr_main() -> None:
    ib = await connect()
    try:
        # pprint(await get_account_information(ib))


        positions_ = get_positions(ib)
        print_positions(positions_)

        for position_ in positions_:
            security_ = await to_security_information(ib, position_)
            pprint(security_)
            print()
            eodhd_security_ = ibkr_to_eodhd_security_information(security_)
            pprint(eodhd_security_)
            pprint(get_last_candle(eodhd_security_))
            print()
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()

    run(_ibkr_main())
