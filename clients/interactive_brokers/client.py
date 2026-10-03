from asyncio import wait_for
from decimal import Decimal
from typing import List, Optional, Sequence

from ib_async import IB, AccountValue, Contract, PortfolioItem

if __package__:
    from . import configuration
    from .domain import AccountInfo, AccountInformation, PortfolioPosition, SecurityInformation
else:
    import configuration
    from domain import AccountInfo, AccountInformation, PortfolioPosition, SecurityInformation

__all__ = ["AccountInformation", "PortfolioPosition", "connect", "disconnect", "get_account_information",
           "get_positions", "print_account_information", "print_positions", "SecurityInformation", "fill_isin",
           "to_security_information"]


def _get_account_pnl(info: AccountInfo, tag: str, currency: str) -> Decimal:
    for currency_ in ("BASE", currency):
        for tag_ in (tag, f"$LEDGER-{tag}"):
            matches_ = [
                value_ for value_ in info.values
                if value_.account == info.account
                   and value_.tag == tag_
                   and not value_.modelCode
                   and value_.currency == currency_
            ]
            if not matches_:
                continue
            if len(matches_) != 1:
                raise ValueError(f"Multiple {tag_} values for account {info.account}.")

            amount_ = Decimal(matches_[0].value)
            if not amount_.is_finite() or amount_ == Decimal("1.7976931348623157E+308"):
                raise ValueError(f"{tag_} is unavailable for account {info.account}.")
            return amount_

    raise ValueError(f"Missing {tag} in the base currency for account {info.account}.")


def _to_account_information(info: AccountInfo) -> AccountInformation:
    fields_: dict[str, str] = {
        "net_liquidation": "NetLiquidation",
        "total_cash": "TotalCashValue",
        "buying_power": "BuyingPower",
        "available_funds": "AvailableFunds",
        "excess_liquidity": "ExcessLiquidity",
        "maintenance_margin": "MaintMarginReq",
    }
    values_: dict[str, Decimal] = {}
    currencies_: set[str] = set()

    for field_, tag_ in fields_.items():
        matches_ = [
            value_ for value_ in info.summary
            if value_.account == info.account
               and value_.tag == tag_
               and not value_.modelCode
        ]
        if len(matches_) != 1:
            raise ValueError(f"Expected one {tag_} value for account {info.account}.")

        value_ = matches_[0]
        if not value_.currency:
            raise ValueError(f"Missing currency for {tag_}.")

        values_[field_] = Decimal(value_.value)
        currencies_.add(value_.currency)

    if len(currencies_) != 1:
        raise ValueError("Account summary amounts have different currencies.")

    currency_ = next(iter(currencies_))
    return AccountInformation(
        account=info.account,
        currency=currency_,
        unrealized_pnl=_get_account_pnl(info, "UnrealizedPnL", currency_),
        realized_pnl=_get_account_pnl(info, "RealizedPnL", currency_),
        **values_,
    )


def _get_positions(
        ib: IB,
        account: Optional[str] = None,
) -> List[PortfolioItem]:
    if not ib.isConnected():
        raise ConnectionError("Connect to IBKR before requesting positions.")

    accounts_ = ib.managedAccounts()
    if account is None:
        if len(accounts_) != 1:
            raise ValueError("Provide an account ID when there is not exactly one managed account.")
        account = accounts_[0]
    else:
        account = account.strip()
        if account not in accounts_:
            raise ValueError(f"Unknown managed account: {account}")

    return list(ib.portfolio(account))


async def _get_account_info(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> AccountInfo:
    if not ib.isConnected():
        raise ConnectionError("Connect to IBKR before requesting account information.")

    accounts_ = ib.managedAccounts()
    if account is None:
        if len(accounts_) != 1:
            raise ValueError("Provide an account ID when there is not exactly one managed account.")
        account = accounts_[0]
    else:
        account = account.strip()
        if account not in accounts_:
            raise ValueError(f"Unknown managed account: {account}")

    account_values_: List[AccountValue] = list(ib.accountValues(account))
    summary_: List[AccountValue] = await wait_for(ib.accountSummaryAsync(account), timeout=timeout)

    return AccountInfo(
        account=account,
        summary=list(summary_),
        values=account_values_,
        positions=list(ib.positions(account)),
        portfolio=list(ib.portfolio(account)),
    )


# PUBLIC

async def connect(
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
        readonly: bool = True,
        timeout: float = 10,
) -> IB:
    ib = IB()
    try:
        await ib.connectAsync(
            host or configuration.host(),
            port or configuration.port(),
            clientId=client_id if client_id is not None else configuration.client_id(),
            readonly=readonly,
            timeout=timeout,
            raiseSyncErrors=True,
        )
    except BaseException:
        ib.disconnect()
        raise

    return ib


def disconnect(ib: IB) -> None:
    ib.disconnect()


async def get_account_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> AccountInformation:
    info_ = await _get_account_info(ib, account, timeout=timeout)
    return _to_account_information(info_)


def _get_return(pnl: Decimal, cost: Decimal) -> Optional[Decimal]:
    return pnl / abs(cost) if cost else None


def get_positions(
        ib: IB,
        account: Optional[str] = None,
) -> List[PortfolioPosition]:
    return [
        PortfolioPosition(
            contract_id=position_.contract.conId,
            symbol=position_.contract.symbol,
            exchange=position_.contract.primaryExchange or position_.contract.exchange,
            currency=position_.contract.currency,
            trading_class=position_.contract.tradingClass,
            quantity=Decimal(str(position_.position)),
            average_cost=Decimal(str(position_.averageCost)),
            total_cost=Decimal(str(position_.position)) * Decimal(str(position_.averageCost)),
            market_price=Decimal(str(position_.marketPrice)),
            market_value=Decimal(str(position_.marketValue)),
            unrealized_pnl=Decimal(str(position_.unrealizedPNL)),
            realized_pnl=Decimal(str(position_.realizedPNL)),
            unrealized_return=_get_return(
                Decimal(str(position_.unrealizedPNL)),
                Decimal(str(position_.position)) * Decimal(str(position_.averageCost)),
            ),
        )
        for position_ in _get_positions(ib, account)
    ]


async def fill_isin(
        ib: IB,
        security: SecurityInformation,
        *,
        timeout: float = 50,
) -> SecurityInformation:
    if not ib.isConnected():
        raise ConnectionError("Connect to IBKR before requesting an ISIN.")

    if security.contract_id is not None:
        if security.contract_id <= 0:
            raise ValueError("contract_id must be positive.")
        contract_ = Contract(conId=security.contract_id)
    else:
        contract_ = Contract(
            secType="STK",
            symbol=security.symbol,
            exchange=security.exchange or "SMART",
            currency=security.currency,
        )

    details_ = await wait_for(ib.reqContractDetailsAsync(contract_), timeout=timeout)
    matches_ = [
        detail_ for detail_ in details_
        if detail_.contract.symbol == security.symbol
        and detail_.contract.currency == security.currency
        and (security.contract_id is None or detail_.contract.conId == security.contract_id)
    ]
    if not matches_:
        raise LookupError(f"No matching contract for {security.symbol} in {security.currency}.")
    if len({detail_.contract.conId for detail_ in matches_}) != 1:
        raise LookupError(f"Multiple contracts match {security.symbol} in {security.currency}.")

    isins_ = {
        identifier_.value
        for detail_ in matches_
        for identifier_ in detail_.secIdList
        if identifier_.tag == "ISIN" and identifier_.value
    }
    if len(isins_) != 1:
        raise LookupError(f"Expected one ISIN for {security.symbol}; received {len(isins_)}.")

    if not security.exchange:
        security.exchange = matches_[0].contract.primaryExchange or matches_[0].contract.exchange
    security.contract_id = matches_[0].contract.conId
    security.isin = next(iter(isins_))
    return security


async def to_security_information(
        ib: IB,
        position: PortfolioPosition,
        *,
        timeout: float = 50,
) -> SecurityInformation:
    security_ = SecurityInformation(
        symbol=position.symbol,
        exchange=position.exchange,
        currency=position.currency,
        contract_id=position.contract_id,
    )
    return await fill_isin(ib, security_, timeout=timeout)


def _print_table(
        headers: List[str],
        rows: List[List[str]],
        *,
        first_right_aligned_column: int,
        separators_after: Sequence[int] = (),
) -> None:
    widths_: List[int] = [
        max(len(header_), *(len(row_[column_]) for row_ in rows))
        for column_, header_ in enumerate(headers)
    ] if rows else [len(header_) for header_ in headers]
    border_ = "+" + "+".join("-" * (width_ + 2) for width_ in widths_) + "+"

    print(border_)
    print("| " + " | ".join(header_.ljust(width_) for header_, width_ in zip(headers, widths_)) + " |")
    print(border_)
    for index_, row_ in enumerate(rows):
        print("| " + " | ".join(
            value_.rjust(widths_[column_]) if column_ >= first_right_aligned_column else value_.ljust(widths_[column_])
            for column_, value_ in enumerate(row_)
        ) + " |")
        if index_ in separators_after and index_ != len(rows) - 1:
            print(border_)
    print(border_)


def print_positions(positions: List[PortfolioPosition]) -> None:
    headers_: List[str] = ["Symbol", "Exchange", "Currency", "Trading class", "Quantity", "Average cost", "Total cost",
                          "Market price", "Market value", "Unrealized PnL", "Realized PnL", "Return",
                          "Contract ID"]
    rows_: List[List[str]] = [
        [
            position_.symbol,
            position_.exchange,
            position_.currency,
            position_.trading_class,
            format(position_.quantity, ",f"),
            format(position_.average_cost, ",f"),
            format(position_.total_cost, ",f"),
            format(position_.market_price, ",f"),
            format(position_.market_value, ",f"),
            format(position_.unrealized_pnl, ",f"),
            format(position_.realized_pnl, ",f"),
            format(position_.unrealized_return, ".2%") if position_.unrealized_return is not None else "",
            str(position_.contract_id),
        ]
        for position_ in positions
    ]
    _print_table(headers_, rows_, first_right_aligned_column=4)
    print(f"({len(rows_)} {'row' if len(rows_) == 1 else 'rows'})")


def print_account_information(information: AccountInformation) -> None:
    rows_: List[List[str]] = [
        ["Net liquidation", format(information.net_liquidation, ",f")],
        ["Unrealized PnL", format(information.unrealized_pnl, ",f")],
        ["Account", information.account],
        ["Currency", information.currency],
        ["Total cash", format(information.total_cash, ",f")],
        ["Buying power", format(information.buying_power, ",f")],
        ["Available funds", format(information.available_funds, ",f")],
        ["Excess liquidity", format(information.excess_liquidity, ",f")],
        ["Maintenance margin", format(information.maintenance_margin, ",f")],
        ["Realized PnL", format(information.realized_pnl, ",f")],
    ]
    _print_table(["Field", "Value"], rows_, first_right_aligned_column=1, separators_after=(1,))
