import os
import time
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional
from risk_engine.risk_metrics import (
    calculate_delta, calculate_gamma, calculate_vega, calculate_theta,
    calculate_var, aggregate_portfolio_risks
)

# Load environment variables
load_dotenv(dotenv_path=".env.local")

DERIBIT_BASE_URL = "https://www.deribit.com/api/v2"
CLIENT_ID = os.getenv("DERIBIT_API_KEY")
CLIENT_SECRET = os.getenv("DERIBIT_API_SECRET")
USE_MOCK = os.getenv("USE_MOCK_OKX", "False").lower() == "true"

class DeribitAPI:
    def __init__(self):
        self.base_url = DERIBIT_BASE_URL
        self.access_token = None
        if not USE_MOCK:
            self.authenticate()

    def authenticate(self):
        url = f"{self.base_url}/public/auth"
        data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        response = requests.get(url, params=data)
        response.raise_for_status()
        self.access_token = response.json()['result']['access_token']

    def _get(self, endpoint, params=None, private=False):
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if private and self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()['result']

    def get_index_price(self, index_name="btc_usd"):
        if USE_MOCK:
            return 57000.0
        result = self._get(f"/public/get_index_price", {"index_name": index_name})
        return result['index_price']

    def get_order_book(self, instrument_name="BTC-PERPETUAL"):
        if USE_MOCK:
            return {"best_bid_price": 56900, "best_ask_price": 57100}
        return self._get(f"/public/get_order_book", {"instrument_name": instrument_name})

    def get_instruments(self, currency="BTC", kind="option"):
        return self._get(f"/public/get_instruments", {"currency": currency, "kind": kind, "expired": False})

    def get_ticker(self, instrument_name):
        return self._get(f"/public/ticker", {"instrument_name": instrument_name})

    def get_account_summary(self, currency="BTC"):
        if USE_MOCK:
            return {"equity": 1.0, "available_funds": 0.8}
        return self._get(f"/private/get_account_summary", {"currency": currency}, private=True)

    def get_positions(self, currency="BTC"):
        # Deribit does not have a direct positions endpoint, so mock or extend as needed
        if USE_MOCK:
            return [
                {"instrument_name": "BTC-30AUG24-60000-C", "size": 1, "kind": "option", "option_type": "call", "S": 57000, "K": 60000, "T": 0.1, "r": 0.05, "sigma": 0.65},
                {"instrument_name": "BTC-PERPETUAL", "size": 0.5, "kind": "future", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}
            ]
        # Otherwise, fetch from API (not implemented here)
        return []

class RiskEngine:
    def __init__(self, deribit_api: DeribitAPI):
        self.api = deribit_api

    def fetch_and_compute(self):
        positions = self.api.get_positions()
        # Compute Greeks for each position
        for pos in positions:
            if pos['kind'] == 'option':
                pos['delta'] = calculate_delta(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'], pos['option_type'])
                pos['gamma'] = calculate_gamma(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'])
                pos['vega'] = calculate_vega(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'])
                pos['theta'] = calculate_theta(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'], pos['option_type'])
            else:
                pos['delta'] = pos['size']
                pos['gamma'] = 0
                pos['vega'] = 0
                pos['theta'] = 0
        agg = aggregate_portfolio_risks(positions)
        # Mock price series for VaR
        price_series = [57000 + 1000 * np.sin(i/5) for i in range(100)]
        var = calculate_var(price_series)
        return {"positions": positions, "aggregate": agg, "VaR": var}

if __name__ == "__main__":
    import numpy as np
    deribit = DeribitAPI()
    engine = RiskEngine(deribit)
    result = engine.fetch_and_compute()
    print("\n--- Real-Time Risk Metrics ---")
    print("Positions:")
    for pos in result["positions"]:
        print(pos)
    print("\nAggregate Portfolio Risk:")
    print(result["aggregate"])
    print(f"\nHistorical VaR: {result['VaR']:.2f}")
