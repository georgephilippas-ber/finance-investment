from asyncio import run

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, print_full_account_information


async def _main() -> None:
    ib = await connect()
    try:
        await print_full_account_information(ib)
    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
