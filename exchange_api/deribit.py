import requests
from config import DERIBIT_BASE_URL, SYMBOL_MAPPINGS

def fetch_spot_price(symbol: str):
    """Fetch the spot price for a given symbol from Deribit."""
    # Deribit does not have a direct spot price endpoint, it's primarily a derivatives exchange.
    # We can get the index price which is close to the spot price.
    instrument_name = f"{symbol.upper()}-PERPETUAL"
    url = f"{DERIBIT_BASE_URL}/public/get_index_price?index_name={symbol.lower()}_usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('result'):
            return float(data['result']['index_price'])
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching index price from Deribit: {e}")
        return None

def fetch_futures_price(symbol: str):
    pass

def fetch_order_book(symbol: str):
    pass

def fetch_open_positions():
    pass
