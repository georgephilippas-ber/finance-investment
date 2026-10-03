from asyncio import run
from pprint import pprint

from dotenv import load_dotenv

from clients.common.mappings import augmented_exchanges_database_ibkr
from clients.eodhd.client import get_symbols_by_ticker, get_symbols_by_isin, read_exchanges_database
from clients.interactive_brokers.client import (SecurityInformation, connect, disconnect, fill_isin,
                                                get_account_information, get_positions, print_positions)


async def _ibkr_main() -> None:
    ib = await connect()
    try:
        pprint(await get_account_information(ib))
        positions_ = get_positions(ib)
        print_positions(positions_)
        for position_ in positions_:
            security_ = SecurityInformation(
                symbol=position_.symbol,
                exchange=position_.exchange,
                currency=position_.currency,
                contract_id=position_.contract_id,
            )
            pprint(await fill_isin(ib, security_))
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()

    print(get_symbols_by_ticker("MSFT", eodhd_code="AS"))

    for s in enumerate(get_symbols_by_isin("DE000A0F5UJ7", currency="EUR")):
        print(s)

    print(augmented_exchanges_database_ibkr(read_exchanges_database()).to_string(index=False))

    run(_ibkr_main())
