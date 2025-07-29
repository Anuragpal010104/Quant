import requests
from config import BYBIT_BASE_URL, SYMBOL_MAPPINGS

def fetch_spot_price(symbol: str):
    """Fetch the spot price for a given symbol from Bybit."""
    instrument_id = SYMBOL_MAPPINGS.get(symbol, symbol)
    url = f"{BYBIT_BASE_URL}/v5/market/tickers?category=spot&symbol={instrument_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('result') and data['result']['list']:
            return float(data['result']['list'][0]['lastPrice'])
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching spot price from Bybit: {e}")
        return None

def fetch_futures_price(symbol: str):
    pass

def fetch_order_book(symbol: str):
    pass

def fetch_open_positions():
    pass
