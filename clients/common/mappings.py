from clients import eodhd
from clients.eodhd.client import get_symbol
from clients.eodhd.client import load_dotenv
if __name__ == "__main__":
    from ib_async import IB, Stock
    load_dotenv()

    print(get_symbol("AMZN", eodhd_code='us'))

    ib = IB()
    ib.connect("127.0.0.1", 4001, clientId=1)

    contract = Stock(
        "AAPL",
        # "SMART",
        # "USD",
        # primaryExchange="NASDAQ",
    )

    details = ib.reqContractDetails(contract)

    for detail in details:
        print(detail)
