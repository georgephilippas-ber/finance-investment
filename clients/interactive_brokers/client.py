from asyncio import wait_for
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import List, Optional

from ib_async import IB, AccountValue, Contract, ContractDetails, LimitOrder, OrderState, PortfolioItem
from ib_async.util import UNSET_DOUBLE

from clients.common.domain import Provider, SecurityInformation
from clients.common.printing import print_table

if __package__:
    from . import configuration
    from .domain import AccountInfo, AccountInformation, LiquidationEstimate, LiquidationSummary, PortfolioPosition
else:
    import configuration
    from domain import AccountInfo, AccountInformation, LiquidationEstimate, LiquidationSummary, PortfolioPosition

__all__ = ["AccountInformation", "PortfolioPosition", "connect", "disconnect", "get_account_information",
           "get_positions", "print_account_information", "print_full_account_information", "print_positions",
           "get_positions_as_security_information"]


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
        limit_discount: Decimal = Decimal(0),
        timeout: float = 50,
) -> AccountInformation:
    information_ = _to_account_information(await _get_account_info(ib, account, timeout=timeout))
    liquidation_ = await _simulate_liquidation(ib, information_, limit_discount, timeout=timeout)
    information_.liquidation_value = liquidation_.cash_after_liquidation
    if information_.total_cost is not None:
        information_.net_return = _get_return(liquidation_.net_proceeds - information_.total_cost,
                                              information_.total_cost)
    return information_


async def _round_to_tick(
        ib: IB,
        details: ContractDetails,
        price: Decimal,
        rounding: str,
        *,
        timeout: float,
) -> Decimal:
    exchanges_ = details.validExchanges.split(",")
    rule_ids_ = details.marketRuleIds.split(",")
    if len(exchanges_) != len(rule_ids_):
        raise LookupError()
    rules_ = {exchange_: int(rule_id_) for exchange_, rule_id_ in zip(exchanges_, rule_ids_)}
    if details.contract.exchange not in rules_:
        raise LookupError()

    increments_ = await wait_for(ib.reqMarketRuleAsync(rules_[details.contract.exchange]), timeout=timeout)
    if not increments_:
        raise LookupError()
    tick_ = max(
        (increment_ for increment_ in increments_ if Decimal(str(increment_.lowEdge)) <= price),
        key=lambda increment_: increment_.lowEdge,
    ).increment
    tick_ = Decimal(str(tick_))

    return (price / tick_).quantize(Decimal(1), rounding=rounding) * tick_


async def _simulate_position_liquidation(
        ib: IB,
        item: PortfolioItem,
        limit_discount: Decimal,
        *,
        timeout: float,
) -> LiquidationEstimate:
    quantity_ = Decimal(str(item.position))
    market_price_ = Decimal(str(item.marketPrice))
    if not market_price_.is_finite() or market_price_ <= 0:
        raise ValueError()

    details_: List[ContractDetails] = await wait_for(
        ib.reqContractDetailsAsync(Contract(conId=item.contract.conId, exchange="SMART")),
        timeout=timeout)

    if len(details_) != 1:
        raise LookupError()

    selling_ = quantity_ > 0
    limit_price_ = await _round_to_tick(
        ib,
        details_[0],
        market_price_ * (1 - limit_discount if selling_ else 1 + limit_discount),
        ROUND_FLOOR if selling_ else ROUND_CEILING,
        timeout=timeout,
    )
    order_ = LimitOrder("SELL" if selling_ else "BUY", float(abs(quantity_)), float(limit_price_), tif="DAY")

    state_ = await wait_for(ib.whatIfOrderAsync(details_[0].contract, order_), timeout=timeout)

    if not isinstance(state_, OrderState) or state_.commission == UNSET_DOUBLE:
        raise LookupError()
    if state_.commissionCurrency != item.contract.currency:
        raise ValueError()

    gross_proceeds_ = quantity_ * limit_price_
    commission_ = Decimal(str(state_.commission))
    return LiquidationEstimate(
        contract_id=item.contract.conId,
        symbol=item.contract.symbol,
        currency=item.contract.currency,
        quantity=quantity_,
        market_price=market_price_,
        limit_price=limit_price_,
        gross_proceeds=gross_proceeds_,
        commission=commission_,
        net_proceeds=gross_proceeds_ - commission_,
    )


async def _simulate_liquidation(
        ib: IB,
        information: AccountInformation,
        limit_discount: Decimal,
        *,
        timeout: float,
) -> LiquidationSummary:
    if not Decimal(0) <= limit_discount < Decimal(1):
        raise ValueError()

    estimates_ = [
        await _simulate_position_liquidation(ib, item_, limit_discount, timeout=timeout)
        for item_ in _get_positions(ib, information.account)
        if item_.position
    ]
    currencies_ = {estimate_.currency for estimate_ in estimates_} - {information.currency}
    if currencies_:
        raise ValueError()

    net_proceeds_ = sum((estimate_.net_proceeds for estimate_ in estimates_), Decimal(0))
    return LiquidationSummary(
        account=information.account,
        currency=information.currency,
        cash=information.total_cash,
        positions=estimates_,
        net_proceeds=net_proceeds_,
        cash_after_liquidation=information.total_cash + net_proceeds_,
    )


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


async def get_positions_as_security_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        timeout: float = 50,
) -> List[SecurityInformation]:
    return await _positions_to_security_information(ib, get_positions(ib, account), timeout=timeout)


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
    print_table(headers_, rows_, first_right_aligned_column=4)
    print(f"({len(rows_)} {'row' if len(rows_) == 1 else 'rows'})")


def print_account_information(information: AccountInformation) -> None:
    rows_: List[List[str]] = [
        ["Account", information.account],
        ["Currency", information.currency],
        ["Portfolio market value", format(information.net_liquidation, ",f")],
        ["Net liquidation",
         format(information.liquidation_value, ",.2f") if information.liquidation_value is not None else ""],
        ["Gross return", format(information.gross_return, ".2%") if information.gross_return is not None else ""],
        ["Net return", format(information.net_return, ".2%") if information.net_return is not None else ""],
        ["Unrealized PnL", format(information.unrealized_pnl, ",f")],
        ["Total cash", format(information.total_cash, ",f")],
        ["Buying power", format(information.buying_power, ",f")],
        ["Available funds", format(information.available_funds, ",f")],
        ["Excess liquidity", format(information.excess_liquidity, ",f")],
        ["Maintenance margin", format(information.maintenance_margin, ",f")],
        ["Realized PnL", format(information.realized_pnl, ",f")],
    ]
    print_table(["Field", "Value"], rows_, first_right_aligned_column=1, separators_after=(1, 3, 6, 11))


async def print_full_account_information(
        ib: IB,
        account: Optional[str] = None,
        *,
        limit_discount: Decimal = Decimal(0),
        timeout: float = 50,
) -> None:
    print_account_information(await get_account_information(ib, account, limit_discount=limit_discount,
                                                            timeout=timeout))
    print_positions(get_positions(ib, account))
