from asyncio import run
from pathlib import Path

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, print_full_account_information
from research.configuration import SCANNER_REFERENCE_FILENAME


async def _main() -> None:
    ib = await connect()

    try:
        scanner_reference = Path(SCANNER_REFERENCE_FILENAME)
        if not scanner_reference.exists():
            scanner_reference.write_text(await ib.reqScannerParametersAsync(), encoding="utf-8")

        await print_full_account_information(ib)

    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
