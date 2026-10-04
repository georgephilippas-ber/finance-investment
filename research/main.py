from asyncio import run
from calendar import monthrange
from datetime import date

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, print_full_account_information
from clients.interactive_brokers.scanner.fixed_income import quote_bonds, interactive_brokers_scan_bonds
from clients.interactive_brokers.scanner.printing import print_bonds, print_bond


def _maturity_date_in_years(years: int) -> str:
    today = date.today()
    year = today.year + years
    day = min(today.day, monthrange(year, today.month)[1])
    return date(year, today.month, day).strftime("%Y%m%d")


async def _main() -> None:
    ib = await connect()

    try:

        await print_full_account_information(ib)

        bonds_corporate_ = await interactive_brokers_scan_bonds(ib, instrument="BOND", location="BOND.EU.EURONEXT",
                                                                scan_code="HIGH_BOND_ASK_YIELD_ALL",
                                                                currencyLike='EUR',
                                                                bondCreditRating='highGrade',
                                                                maturityDateAbove=_maturity_date_in_years(2),
                                                                maturityDateBelow=_maturity_date_in_years(3),
                                                                bondCallableIs='false',
                                                                excludeConvertible='true',
                                                                bondVarCouponRateIs='false',
                                                                bondDefaultedIs='false',
                                                                bondAmtOutstandingAbove=100,
                                                                bondInitialSizeAbove=1,
                                                                bondInitialSizeBelow=10,
                                                                )

        quoted_corporate_ = await quote_bonds(ib, bonds_corporate_)
        print()
        print_bonds(quoted_corporate_, title="EUR INVESTMENT-GRADE CORPORATES, 2-5 YEARS")
        print()
        print_bond(quoted_corporate_[0])


    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
