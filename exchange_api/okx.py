import requests
from config import OKX_BASE_URL, SYMBOL_MAPPINGS

def fetch_spot_price(symbol: str):
    """Fetch the spot price for a given symbol from OKX."""
    instrument_id = SYMBOL_MAPPINGS.get(symbol, symbol)
    url = f"{OKX_BASE_URL}/market/ticker?instId={instrument_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        if data['data']:
            return float(data['data'][0]['last'])
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching spot price from OKX: {e}")
        return None

def fetch_futures_price(symbol: str):
    pass

def fetch_order_book(symbol: str):
    pass

def fetch_open_positions():
    pass
