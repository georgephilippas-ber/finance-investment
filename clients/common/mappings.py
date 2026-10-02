from ib_async import Contract

from clients.eodhd.client import load_dotenv

if __name__ == "__main__":
    from ib_async import IB

    load_dotenv()

    # print(get_symbol("AMZN", eodhd_code='us'))

    ib = IB()
    ib.connect("127.0.0.1", 4001, clientId=1)

    contract = Contract(
        # secType="STK",
        secIdType="ISIN",
        secId="US0231351067",
        currency="USD",
        exchange="SMART",
    )

    details = ib.reqContractDetails(contract)

    print(details[0])
