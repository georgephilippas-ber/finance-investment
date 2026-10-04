from asyncio import wait_for
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from sqlite3 import OperationalError
from typing import List, Optional, Tuple

from babel.numbers import format_compact_currency, format_currency
from ib_async import IB, AccountValue, Contract, PortfolioItem
from ib_async.util import UNSET_DOUBLE

from clients.common.domain import Provider, SecurityInformation
from printing import print_table

if __package__:
    from . import configuration, position_tracker
    from .domain import AccountInfo, AccountInformation, PortfolioPosition
else:
    import configuration
    import position_tracker
    from domain import AccountInfo, AccountInformation, PortfolioPosition

__all__ = ["AccountInformation", "PortfolioPosition", "connect", "disconnect", "get_account_information",
           "get_commission", "get_positions", "print_account_information", "print_full_account_information",
           "print_positions", "get_positions_as_security_information"]


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
            if not amount_.is_finite() or amount_ == Decimal(str(UNSET_DOUBLE)):
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
    unrealized_pnl_ = _get_account_pnl(info, "UnrealizedPnL", currency_)

    cost_ = None
    if all(item_.contract.currency == currency_ for item_ in info.portfolio):
        cost_ = sum(
            (Decimal(str(item_.position)) * Decimal(str(item_.averageCost)) for item_ in info.portfolio),
            Decimal(0),
        )

    return AccountInformation(
        account=info.account,
        currency=currency_,
        unrealized_pnl=unrealized_pnl_,
        realized_pnl=_get_account_pnl(info, "RealizedPnL", currency_),
        total_cost=cost_,
        gross_return=_get_return(unrealized_pnl_, cost_) if cost_ is not None else None,
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


async def _fill_isin(
        ib: IB,
        security: SecurityInformation,
        *,
        timeout: float = 50,
) -> SecurityInformation:
    if not ib.isConnected():
        raise ConnectionError("Connect to IBKR before requesting an ISIN.")
    if security.provider is not Provider.IBKR:
        raise ValueError()

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


async def _positions_to_security_information(
        ib: IB,
        positions: List[PortfolioPosition],
        *,
        timeout: float = 50,
) -> List[SecurityInformation]:
    return [
        await _fill_isin(
            ib,
            SecurityInformation(
                provider=Provider.IBKR,
                symbol=position_.symbol,
                exchange=position_.exchange,
                currency=position_.currency,
                contract_id=position_.contract_id,
            ),
            timeout=timeout,
        )
        for position_ in positions
    ]



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


def get_commission(quantity: Decimal, price: Decimal, currency: str) -> Decimal:
    shares_ = abs(quantity)
    value_ = shares_ * price
    match currency:
        case "EUR":
            commission_ = max(Decimal(3), value_ * Decimal("0.0005"))
        case "USD":
            commission_ = min(max(Decimal(1), shares_ * Decimal("0.005")), value_ * Decimal("0.01"))
        case _:
            raise LookupError()
    return commission_.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_liquidation_proceeds(items: List[PortfolioItem], currency: str) -> Optional[Decimal]:
    proceeds_ = Decimal(0)
    for item_ in items:
        if not item_.position:
            continue
        price_ = Decimal(str(item_.marketPrice))
        value_ = Decimal(str(item_.marketValue))
        if item_.contract.currency != currency or not price_.is_finite() or not value_.is_finite():
            return None
        try:
            commission_ = get_commission(Decimal(str(item_.position)), price_, item_.contract.currency)
        except LookupError:
            return None
        proceeds_ += value_ - commission_
    return proceeds_


async def get_account_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> AccountInformation:
    information_ = _to_account_information(await _get_account_info(ib, account, timeout=timeout))
    proceeds_ = _get_liquidation_proceeds(_get_positions(ib, information_.account), information_.currency)
    if proceeds_ is not None:
        information_.liquidation_value = information_.total_cash + proceeds_
        if information_.total_cost is not None:
            information_.net_return = _get_return(proceeds_ - information_.total_cost, information_.total_cost)
    return information_


def _get_return(pnl: Decimal, cost: Decimal) -> Optional[Decimal]:
    return pnl / abs(cost) if cost else None


def _get_holding(contract_id: int) -> Tuple[Optional[date], Optional[Decimal]]:
    if not position_tracker.DEFAULT_PATH.exists():
        return None, None
    try:
        lots_ = position_tracker.PositionTracker.by_contract_id(contract_id)
    except (OperationalError, RuntimeError):
        return None, None
    quantity_ = sum((lot_.quantity for lot_ in lots_), Decimal(0))
    if not lots_ or quantity_ <= 0:
        return (min(lot_.opened for lot_ in lots_) if lots_ else None), None

    today_ = date.today()
    days_ = sum((lot_.quantity * (today_ - lot_.opened).days for lot_ in lots_), Decimal(0)) / quantity_
    return min(lot_.opened for lot_ in lots_), days_


def _get_annualized_return(hpr: Optional[Decimal], days: Optional[Decimal]) -> Optional[Decimal]:
    if hpr is None or days is None or days < 365 or hpr <= -1:
        return None
    return (1 + hpr) ** (Decimal(365) / days) - 1


def get_positions(
        ib: IB,
        account: Optional[str] = None,
) -> List[PortfolioPosition]:
    positions_: List[PortfolioPosition] = []
    for position_ in _get_positions(ib, account):
        total_cost_ = Decimal(str(position_.position)) * Decimal(str(position_.averageCost))
        hpr_ = _get_return(Decimal(str(position_.unrealizedPNL)), total_cost_)
        opened_, days_ = _get_holding(position_.contract.conId)
        positions_.append(PortfolioPosition(
            contract_id=position_.contract.conId,
            symbol=position_.contract.symbol,
            exchange=position_.contract.primaryExchange or position_.contract.exchange,
            currency=position_.contract.currency,
            trading_class=position_.contract.tradingClass,
            quantity=Decimal(str(position_.position)),
            average_cost=Decimal(str(position_.averageCost)),
            total_cost=total_cost_,
            market_price=Decimal(str(position_.marketPrice)),
            market_value=Decimal(str(position_.marketValue)),
            unrealized_pnl=Decimal(str(position_.unrealizedPNL)),
            realized_pnl=Decimal(str(position_.realizedPNL)),
            unrealized_hpr=hpr_,
            opened=opened_,
            unrealized_annualized_return=_get_annualized_return(hpr_, days_),
        ))
    return positions_


async def get_positions_as_security_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> List[SecurityInformation]:
    return await _positions_to_security_information(ib, get_positions(ib, account), timeout=timeout)


def print_positions(positions: List[PortfolioPosition]) -> None:
    headers_: List[str] = ["Contract ID", "Opened", "Symbol", "Exchange", "Quantity", "Total cost", "Market price",
                           "Market value", "Unrealized PnL", "Return", "Annual Return"]
    rows_: List[List[str]] = [
        [
            str(position_.contract_id),
            position_.opened.isoformat() if position_.opened is not None else "-",
            position_.symbol,
            position_.exchange,
            format(position_.quantity, ",f"),
            _format_money(position_.total_cost, position_.currency),
            _format_money(position_.market_price, position_.currency),
            _format_money(position_.market_value, position_.currency),
            _format_money(position_.unrealized_pnl, position_.currency),
            format(position_.unrealized_hpr, ".2%") if position_.unrealized_hpr is not None else "-",
            format(position_.unrealized_annualized_return, ".2%")
            if position_.unrealized_annualized_return is not None else "-",
        ]
        for position_ in positions
    ]
    print_table(headers_, rows_, first_right_aligned_column=4, title="OPEN POSITIONS")
    print(f"({len(rows_)} {'row' if len(rows_) == 1 else 'rows'})")


def _format_money(amount: Optional[Decimal], currency: str) -> str:
    if amount is None:
        return "-"
    if abs(amount) >= 1_000_000:
        return format_compact_currency(amount, currency, locale="en_US", fraction_digits=2)
    return format_currency(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), currency, locale="en_US")


def print_account_information(information: AccountInformation) -> None:
    currency_ = information.currency
    rows_: List[List[str]] = [
        ["Account", information.account],
        ["Currency", currency_],
        ["Portfolio market value", _format_money(information.net_liquidation, currency_)],
        ["Net liquidation", _format_money(information.liquidation_value, currency_)],
        ["Gross return", format(information.gross_return, ".2%") if information.gross_return is not None else "-"],
        ["Net return", format(information.net_return, ".2%") if information.net_return is not None else "-"],
        ["Unrealized PnL", _format_money(information.unrealized_pnl, currency_)],
        ["Total cash", _format_money(information.total_cash, currency_)],
        ["Buying power", _format_money(information.buying_power, currency_)],
        ["Available funds", _format_money(information.available_funds, currency_)],
        ["Excess liquidity", _format_money(information.excess_liquidity, currency_)],
        ["Maintenance margin", _format_money(information.maintenance_margin, currency_)],
        ["Realized PnL", _format_money(information.realized_pnl, currency_)],
    ]
    print_table(["Field", "Value"], rows_, first_right_aligned_column=1, separators_after=(1, 3, 6, 11),
                title="ACCOUNT SUMMARY")


async def print_full_account_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> None:
    print_account_information(await get_account_information(ib, account, timeout=timeout))
    print()
    print_positions(get_positions(ib, account))
