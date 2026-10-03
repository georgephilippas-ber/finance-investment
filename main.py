from asyncio import run

from dotenv import load_dotenv

from clients.interactive_brokers.client import (connect, disconnect, get_account_information, get_positions,
                                                print_account_information, print_positions, simulate_liquidation)


async def _main() -> None:
    ib = await connect()
    try:
        print_account_information(await get_account_information(ib))
        print_positions(get_positions(ib))
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
