import os
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv(dotenv_path=".env.local")

# Base URLs for exchange APIs
OKX_BASE_URL = "https://www.okx.com/api/v5"
BYBIT_BASE_URL = "https://api.bybit.com"
DERIBIT_BASE_URL = "https://www.deribit.com/api/v2"

# Symbol mapping used for consistency
SYMBOL_MAPPINGS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT"
}

# API Keys (fetched securely from environment variables)
OKX_API_KEY = os.getenv("OKX_API_KEY", "")
OKX_API_SECRET = os.getenv("OKX_API_SECRET", "")

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")

DERIBIT_API_KEY = os.getenv("DERIBIT_API_KEY", "")
DERIBIT_API_SECRET = os.getenv("DERIBIT_API_SECRET", "")

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# --- Bonus: Dynamic strike/expiry optimization toggle ---
DYNAMIC_STRIKE_EXPIRY_OPTIMIZATION = os.getenv("DYNAMIC_STRIKE_EXPIRY_OPTIMIZATION", "false").lower() == "true"

def get_config():
    """
    Returns a config dictionary for use in other modules.
    """
    return {
        'OKX_API_KEY': OKX_API_KEY,
        'OKX_API_SECRET': OKX_API_SECRET,
        'BYBIT_API_KEY': BYBIT_API_KEY,
        'BYBIT_API_SECRET': BYBIT_API_SECRET,
        'DERIBIT_API_KEY': DERIBIT_API_KEY,
        'DERIBIT_API_SECRET': DERIBIT_API_SECRET,
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'DYNAMIC_STRIKE_EXPIRY_OPTIMIZATION': DYNAMIC_STRIKE_EXPIRY_OPTIMIZATION,
        # Add more config values as needed
    }
