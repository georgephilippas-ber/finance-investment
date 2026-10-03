from asyncio import run

from clients.interactive_brokers.client import print_full_account_information, connect

if __name__ == "__main__":
    async def main():
        client_ = await connect()

        await print_full_account_information(client_)
        client_.disconnect()


    run(main())
