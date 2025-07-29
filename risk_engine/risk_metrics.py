import numpy as np
import pandas as pd
from scipy.stats import norm
import math
from typing import List, Dict, Optional
import os
import csv
from config import get_config  # Assumes get_config() returns a dict or has a method to get config values

def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    """
    Calculate Black-Scholes price for European options.
    """
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return price

def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    if option_type == 'call':
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1

def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))

def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return S * norm.pdf(d1) * math.sqrt(T) / 100  # Per 1% change in vol

def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == 'call':
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
    return theta

def calculate_var(price_series: List[float], confidence_level: float = 0.95) -> float:
    returns = np.diff(np.log(price_series))
    mean = np.mean(returns)
    std = np.std(returns)
    var = norm.ppf(1 - confidence_level, mean, std) * np.mean(price_series)
    return abs(var)

def calculate_correlation_matrix(price_dict: Dict[str, List[float]]) -> pd.DataFrame:
    df = pd.DataFrame(price_dict)
    return df.pct_change().corr()

def aggregate_portfolio_risks(positions: List[Dict], use_dynamic_optimization: Optional[bool] = None) -> Dict:
    """
    Aggregates portfolio Greeks. If use_dynamic_optimization is True (or config enabled),
    applies dynamic strike/expiry optimization logic (placeholder for advanced logic).
    """
    if use_dynamic_optimization is None:
        from config import get_config
        use_dynamic_optimization = get_config().get('DYNAMIC_STRIKE_EXPIRY_OPTIMIZATION', False)
    # Placeholder: If enabled, you could optimize the positions list here
    # For now, just log the toggle and proceed as normal
    if use_dynamic_optimization:
        print("[INFO] Dynamic strike/expiry optimization enabled for risk aggregation.")
    total_delta = 0
    total_gamma = 0
    total_vega = 0
    total_theta = 0
    for pos in positions:
        size = pos.get('position_size', 1)
        if pos['type'] == 'option':
            delta = calculate_delta(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'], pos['option_type']) * size
            gamma = calculate_gamma(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma']) * size
            vega = calculate_vega(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma']) * size
            theta = calculate_theta(pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'], pos['option_type']) * size
        else:
            delta = size
            gamma = 0
            vega = 0
            theta = 0
        total_delta += delta
        total_gamma += gamma
        total_vega += vega
        total_theta += theta
    return {
        'delta': total_delta,
        'gamma': total_gamma,
        'vega': total_vega,
        'theta': total_theta
    }

def import_historical_csv(csv_path: str) -> pd.DataFrame:
    """
    Import historical options data from Deribit/Bybit CSV export.
    Returns a pandas DataFrame with parsed data.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    return df

# --- Dynamic strike/expiry optimization toggle ---
def is_dynamic_hedge_optimization_enabled() -> bool:
    """
    Returns True if dynamic strike/expiry optimization is enabled in config, else False.
    """
    config = get_config()
    return config.get('DYNAMIC_HEDGE_OPTIMIZATION', False)

# --- Example usage in optimize_option_hedge ---
def optimize_option_hedge(options_chain: List[Dict], target_delta: float, enable_optimization: Optional[bool] = None) -> Dict:
    """
    Selects the optimal option (strike/expiry) to hedge target_delta.
    If enable_optimization is None, uses config toggle.
    """
    if enable_optimization is None:
        enable_optimization = is_dynamic_hedge_optimization_enabled()
    if not enable_optimization:
        # Default: pick ATM option with nearest expiry
        atm = min(options_chain, key=lambda x: abs(x['S'] - x['K']))
        return atm
    # Dynamic optimization: minimize cost, slippage, or maximize hedge efficiency
    # Example: pick option with delta closest to target_delta, then lowest cost
    best = min(options_chain, key=lambda x: (abs(x['delta'] - target_delta), x.get('ask', 1e9)))
    return best

# --- Bonus: Import positions from Deribit/Bybit CSV ---
def import_positions_from_csv(csv_path: str) -> list:
    """
    Import positions from a Deribit/Bybit historical CSV and convert to internal format.
    Auto-detects columns for symbol, type, strike, expiry, etc.
    Returns a list of position dicts.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    # Try to auto-detect columns
    colmap = {}
    for col in df.columns:
        lcol = col.lower()
        if 'strike' in lcol:
            colmap['K'] = col
        elif 'expiry' in lcol or 'maturity' in lcol:
            colmap['expiry'] = col
        elif 'type' in lcol:
            colmap['option_type'] = col
        elif 'size' in lcol or 'qty' in lcol:
            colmap['position_size'] = col
        elif 'underlying' in lcol or 'symbol' in lcol:
            colmap['symbol'] = col
        elif 'price' in lcol and 'mark' not in lcol:
            colmap['S'] = col
        elif 'vol' in lcol:
            colmap['sigma'] = col
    positions = []
    for _, row in df.iterrows():
        pos = {
            'type': 'option' if 'option' in str(row.get(colmap.get('option_type', ''), '')).lower() else 'spot',
            'S': float(row.get(colmap.get('S', ''), 0)),
            'K': float(row.get(colmap.get('K', ''), 0)),
            'T': 0.01,  # Placeholder: should compute time to expiry from 'expiry' if available
            'r': 0.0,   # Placeholder: risk-free rate
            'sigma': float(row.get(colmap.get('sigma', ''), 0.5)),
            'option_type': str(row.get(colmap.get('option_type', ''), 'call')).lower(),
            'position_size': float(row.get(colmap.get('position_size', ''), 1)),
            'symbol': row.get(colmap.get('symbol', ''), ''),
        }
        # Compute T if expiry is available
        if 'expiry' in colmap:
            try:
                expiry = pd.to_datetime(row[colmap['expiry']])
                now = pd.Timestamp.utcnow()
                T = max((expiry - now).total_seconds() / (365 * 24 * 3600), 0.001)
                pos['T'] = T
            except Exception:
                pass
        positions.append(pos)
    return positions
