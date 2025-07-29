from utils.logger import logger
from exchange_api.okx import fetch_spot_price as fetch_okx_spot_price
from exchange_api.bybit import fetch_spot_price as fetch_bybit_spot_price
from exchange_api.deribit import fetch_spot_price as fetch_deribit_spot_price
import telegram_bot
import os
import asyncio
import json
from dotenv import load_dotenv
from tabulate import tabulate
from exchange_api.deribit_api import DeribitClient
from risk_engine.risk_metrics import (
    calculate_delta, calculate_gamma, calculate_vega, calculate_theta,
    aggregate_portfolio_risks, calculate_var
)

# Load environment variables
load_dotenv(dotenv_path=".env.local")
USE_MOCK = os.getenv("USE_MOCK_DERIBIT", "False").lower() == "true"

# Try to load mock positions from file, else use hardcoded
MOCK_POSITIONS_PATH = "mock_positions.json"
def load_mock_positions():
    if os.path.exists(MOCK_POSITIONS_PATH):
        with open(MOCK_POSITIONS_PATH, "r") as f:
            return json.load(f)
    # Fallback: hardcoded
    return [
        {"instrument_name": "BTC-30AUG24-60000-C", "size": 1, "type": "option", "option_type": "call", "S": 57000, "K": 60000, "T": 0.1, "r": 0.05, "sigma": 0.65},
        {"instrument_name": "BTC-PERPETUAL", "size": 0.5, "type": "spot", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}
    ]

async def main():
    logger.info("Starting the trading bot...")

    btc_price_okx = fetch_okx_spot_price("BTC")
    logger.info(f"BTC price on OKX: {btc_price_okx}")

    btc_price_bybit = fetch_bybit_spot_price("BTC")
    logger.info(f"BTC price on Bybit: {btc_price_bybit}")

    btc_price_deribit = fetch_deribit_spot_price("BTC")
    logger.info(f"BTC price on Deribit: {btc_price_deribit}")

    client = DeribitClient()
    await client.authenticate()
    positions = load_mock_positions()

    # Fetch spot and perpetual prices
    spot_price = None
    perp_price = None
    if not USE_MOCK:
        try:
            spot_price = (await client.get_orderbook("BTC-30AUG24-60000-C")).get("index_price")
            perp_price = (await client.get_orderbook("BTC-PERPETUAL")).get("mark_price")
        except Exception:
            spot_price = perp_price = None
    else:
        spot_price = 57000
        perp_price = 57000

    # Compute Greeks for each position
    for pos in positions:
        if pos["type"] == "option":
            pos["delta"] = calculate_delta(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"], pos["option_type"])
            pos["gamma"] = calculate_gamma(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"])
            pos["vega"] = calculate_vega(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"])
            pos["theta"] = calculate_theta(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"], pos["option_type"])
        else:
            pos["delta"] = pos["size"]
            pos["gamma"] = 0
            pos["vega"] = 0
            pos["theta"] = 0

    # Aggregate portfolio metrics
    agg = aggregate_portfolio_risks(positions)
    # Mock price series for VaR
    price_series = [57000 + 1000 * __import__('math').sin(i/5) for i in range(100)]
    var = calculate_var(price_series)

    # Print results
    print("\n--- Deribit Risk Metrics CLI ---\n")
    print(f"Spot Price: {spot_price}")
    print(f"Perpetual Mark Price: {perp_price}")
    print("\nPositions:")
    print(tabulate([
        [p["instrument_name"], p["size"], p["type"], p.get("delta"), p.get("gamma"), p.get("vega"), p.get("theta")]
        for p in positions
    ], headers=["Instrument", "Size", "Type", "Delta", "Gamma", "Vega", "Theta"]))
    print("\nAggregate Portfolio Risk:")
    print(tabulate([[agg["delta"], agg["gamma"], agg["vega"], agg["theta"]]], headers=["Delta", "Gamma", "Vega", "Theta"]))
    print(f"\nHistorical VaR: {var:.2f}")
    await client.close()

# Start the telegram bot
# telegram_bot.main()

if __name__ == "__main__":
    asyncio.run(main())
