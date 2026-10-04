from asyncio import run
from calendar import monthrange
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, print_full_account_information
from clients.interactive_brokers.scanner.fixed_income import quote_bonds, scan_bonds
from clients.interactive_brokers.scanner.printing import print_bond
from research.configuration import SCANNER_REFERENCE_FILENAME


def _maturity_date_in_years(years: int) -> str:
    today = date.today()
    year = today.year + years
    day = min(today.day, monthrange(year, today.month)[1])
    return date(year, today.month, day).strftime("%Y%m%d")


async def _main() -> None:
    ib = await connect()

    try:
        # scanner_reference = Path(SCANNER_REFERENCE_FILENAME)
        # if not scanner_reference.exists():
        #     scanner_reference.write_text(await ib.reqScannerParametersAsync(), encoding="utf-8")

        await print_full_account_information(ib)

        # bonds_government_ = await scan_bonds(ib, instrument="BOND.GOVT.NON-US", location="BOND.GOVT.NON-US",
        #                                      scan_code="HIGH_BOND_ASK_YIELD_ALL",
        #                                      issuerCountryIs='DE',
        #                                      currencyLike='EUR',
        #                                      maturityDateAbove=_maturity_date_in_years(2),
        #                                      maturityDateBelow=_maturity_date_in_years(5))
        #
        # for bond_ in await quote_bonds(ib, bonds_government_[:3]):
        #     print()
        #     print_bond(bond_)

        bonds_corporate_ = await scan_bonds(ib, instrument="BOND", location="BOND.WW",
                                            scan_code="HIGH_BOND_ASK_YIELD_ALL",
                                            currencyLike='EUR',
                                            bondCreditRating='highGrade',
                                            maturityDateAbove=_maturity_date_in_years(2),
                                            maturityDateBelow=_maturity_date_in_years(5),
                                            bondCallableIs='false',
                                            excludeConvertible='true',
                                            bondVarCouponRateIs='false',
                                            bondDefaultedIs='false',
                                            bondAmtOutstandingAbove=500)

        for bond_ in await quote_bonds(ib, bonds_corporate_[:3]):
            print()
            print_bond(bond_)

    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
