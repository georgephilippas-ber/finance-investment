from asyncio import run
from pprint import pprint

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, get_account_information, get_positions, print_positions


async def _main() -> None:
    ib = await connect()
    try:
        pprint(await get_account_information(ib))
        print_positions(get_positions(ib))
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
