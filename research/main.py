from asyncio import run

from dotenv import load_dotenv

from clients.interactive_brokers.client import connect, disconnect, print_full_account_information
from clients.interactive_brokers.scanners.fixed_income import quote_bonds, interactive_brokers_scan_bonds
from clients.interactive_brokers.scanners.printing import print_bonds_table, print_bond, print_bonds


async def _main() -> None:
    ib = await connect()

    try:

        await print_full_account_information(ib)

        bonds_corporate_ = await interactive_brokers_scan_bonds(ib,
                                                                instrument="BOND",
                                                                location="BOND.EU.EURONEXT",
                                                                scan_code="HIGH_BOND_ASK_YIELD_ALL",
                                                                currencyLike='EUR',
                                                                bondCreditRating='highGrade',
                                                                maturityYearsAbove=2,
                                                                maturityYearsBelow=3,
                                                                bondCallableIs=False,
                                                                excludeConvertible=True,
                                                                bondVarCouponRateIs=False,
                                                                bondDefaultedIs=False,
                                                                bondAmtOutstandingAbove=100,
                                                                bondInitialSizeAbove=1,
                                                                bondInitialSizeBelow=1000,
                                                                )

        quoted_corporate_ = await quote_bonds(ib, bonds_corporate_)
        print()
        print_bonds_table(quoted_corporate_, title="EUR INVESTMENT-GRADE CORPORATES, 2-5 YEARS")
        print()
        print_bonds(quoted_corporate_, max_rows=4)

        bonds_high_yield_ = await interactive_brokers_scan_bonds(ib,
                                                                 instrument="BOND",
                                                                 location="BOND.EU.EURONEXT",
                                                                 scan_code="HIGH_BOND_ASK_YIELD_ALL",
                                                                 currencyLike='EUR',
                                                                 bondCreditRating='highYield',
                                                                 bondCallableIs=True,
                                                                 maturityYearsAbove=2,
                                                                 maturityYearsBelow=3,
                                                                 excludeConvertible=True,
                                                                 bondVarCouponRateIs=False,
                                                                 bondDefaultedIs=False,
                                                                 bondAmtOutstandingAbove=100,
                                                                 bondInitialSizeAbove=1,
                                                                 bondInitialSizeBelow=1000,
                                                                 )

        quoted_high_yield_ = await quote_bonds(ib, bonds_high_yield_)
        print()
        print_bonds_table(quoted_high_yield_, title="EUR HIGH-YIELD CORPORATES, 2-3 YEARS", max_rows=10)

    finally:
        disconnect(ib)


if __name__ == "__main__":
    load_dotenv()
    run(_main())
