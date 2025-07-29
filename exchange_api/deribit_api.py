import os
import asyncio
import httpx
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv(dotenv_path=".env.local")

DERIBIT_BASE_URL = "https://www.deribit.com/api/v2"
DERIBIT_CLIENT_ID = os.getenv("DERIBIT_API_KEY")
DERIBIT_CLIENT_SECRET = os.getenv("DERIBIT_API_SECRET")
USE_MOCK = os.getenv("USE_MOCK_DERIBIT", "False").lower() == "true"

class DeribitClient:
    def __init__(self):
        self.base_url = DERIBIT_BASE_URL
        self.client_id = DERIBIT_CLIENT_ID
        self.client_secret = DERIBIT_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self._client = httpx.AsyncClient()

    async def authenticate(self):
        if USE_MOCK:
            self.access_token = "mock_token"
            return
        url = f"{self.base_url}/public/auth"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        for _ in range(3):
            try:
                resp = await self._client.get(url, params=params, timeout=10)
                resp.raise_for_status()
                self.access_token = resp.json()["result"]["access_token"]
                return
            except Exception as e:
                await asyncio.sleep(1)
        raise RuntimeError("Failed to authenticate with Deribit API.")

    async def _request(self, endpoint: str, params: dict = None, private: bool = False) -> Dict[str, Any]:
        if USE_MOCK:
            return {"mock": True}
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if private and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        for _ in range(3):
            try:
                resp = await self._client.get(url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                return resp.json()["result"]
            except Exception as e:
                await asyncio.sleep(1)
        raise RuntimeError(f"Failed to fetch {endpoint} from Deribit API.")

    async def get_orderbook(self, instrument_name: str) -> Dict[str, Any]:
        if USE_MOCK:
            return {"bids": [[57000, 1]], "asks": [[57100, 1]]}
        return await self._request("/public/get_order_book", {"instrument_name": instrument_name})

    async def get_instruments(self, currency: str = "BTC", kind: str = "option") -> Dict[str, Any]:
        if USE_MOCK:
            return {"instruments": [
                {"instrument_name": "BTC-30AUG24-60000-C", "kind": "option", "option_type": "call"}
            ]}
        return await self._request("/public/get_instruments", {"currency": currency, "kind": kind, "expired": False})

    async def get_account_summary(self, currency: str = "BTC") -> Dict[str, Any]:
        if USE_MOCK:
            return {"equity": 1.0, "available_funds": 0.8}
        return await self._request("/private/get_account_summary", {"currency": currency}, private=True)

    async def close(self):
        await self._client.aclose()

# Example usage (for testing):
if __name__ == "__main__":
    async def main():
        client = DeribitClient()
        await client.authenticate()
        ob = await client.get_orderbook("BTC-PERPETUAL")
        print("Orderbook:", ob)
        instr = await client.get_instruments()
        print("Instruments:", instr)
        acct = await client.get_account_summary()
        print("Account Summary:", acct)
        await client.close()
    asyncio.run(main())
