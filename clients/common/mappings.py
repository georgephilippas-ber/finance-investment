from asyncio import wait_for

from ib_async import IB, Contract

from clients.common.domain import Provider, SecurityInformation
from clients.common.exchanges import get_augmented_exchanges_database
from clients.eodhd.client import get_security_information_by_isin

__all__ = ["SecurityInformationMapping"]


class SecurityInformationMapping:
    @staticmethod
    def from_ibkr_to_eodhd(security: SecurityInformation) -> SecurityInformation:
        if security.provider is not Provider.IBKR or not security.isin:
            raise ValueError()

        exchanges_ = get_augmented_exchanges_database()
        matches_ = exchanges_.loc[
            (exchanges_["ibkr_exchange"] == security.exchange)
            | exchanges_["ibkr_other_exchanges"].map(lambda codes: security.exchange in codes)
            ]
        eodhd_codes_ = set(matches_["eodhd_code"])
        if len(eodhd_codes_) != 1:
            raise LookupError()
        eodhd_code_ = next(iter(eodhd_codes_))

        tickers_ = {
            listing_.symbol for listing_ in get_security_information_by_isin(security.isin, currency=security.currency)
            if listing_.exchange == eodhd_code_
        }
        if len(tickers_) != 1:
            raise LookupError()

        return SecurityInformation(
            provider=Provider.EODHD,
            symbol=next(iter(tickers_)),
            exchange=eodhd_code_,
            isin=security.isin,
            currency=security.currency,
        )

    @staticmethod
    async def from_eodhd_to_ibkr(
            ib: IB,
            security: SecurityInformation,
            *,
            timeout: float = 50,
    ) -> SecurityInformation:
        if security.provider is not Provider.EODHD or not security.isin:
            raise ValueError()

        exchanges_ = get_augmented_exchanges_database()
        matches_ = exchanges_.loc[exchanges_["eodhd_code"] == security.exchange]
        ibkr_codes_ = {code_ for code_ in matches_["ibkr_exchange"] if code_} | {
            code_ for codes_ in matches_["ibkr_other_exchanges"] for code_ in codes_
        }
        if not ibkr_codes_:
            raise LookupError()

        details_ = await wait_for(
            ib.reqContractDetailsAsync(Contract(secType="STK", secIdType="ISIN", secId=security.isin)),
            timeout=timeout,
        )
        contracts_ = {
            detail_.contract.conId: detail_.contract
            for detail_ in details_
            if detail_.contract.currency == security.currency and detail_.contract.primaryExchange in ibkr_codes_
        }
        if len(contracts_) != 1:
            raise LookupError()
        contract_ = next(iter(contracts_.values()))

        return SecurityInformation(
            provider=Provider.IBKR,
            symbol=contract_.symbol,
            exchange=contract_.primaryExchange,
            currency=security.currency,
            isin=security.isin,
            contract_id=contract_.conId,
        )
