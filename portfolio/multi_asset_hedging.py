import pandas as pd
import numpy as np

def calculate_cross_asset_correlation(price_data: dict) -> pd.DataFrame:
    """
    Calculate correlation matrix for multiple assets.
    price_data: { 'BTC': [...], 'ETH': [...], ... }
    """
    df = pd.DataFrame(price_data)
    return df.pct_change().corr()

def compute_portfolio_exposure(positions: list) -> dict:
    """
    Calculate total delta, gamma, vega, theta by asset.
    Returns: { 'BTC': {'delta': ..., 'gamma': ...}, ... }
    """
    exposures = {}
    for pos in positions:
        asset = pos.get('symbol')
        if asset not in exposures:
            exposures[asset] = {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0}
        exposures[asset]['delta'] += pos.get('delta', 0)
        exposures[asset]['gamma'] += pos.get('gamma', 0)
        exposures[asset]['vega'] += pos.get('vega', 0)
        exposures[asset]['theta'] += pos.get('theta', 0)
    return exposures

def optimal_hedge_allocation(exposures: dict, corr_matrix: pd.DataFrame) -> dict:
    """
    Allocate hedge weights across assets using delta exposures and correlation matrix.
    Returns: { 'BTC': hedge_size, 'ETH': hedge_size, ... }
    """
    assets = list(exposures.keys())
    deltas = np.array([exposures[a]['delta'] for a in assets])
    # Invert correlation matrix for risk-parity-like allocation
    try:
        inv_corr = np.linalg.pinv(corr_matrix.values)
        weights = -inv_corr @ deltas
        # Normalize weights to total delta magnitude
        total_abs = np.sum(np.abs(weights))
        if total_abs > 0:
            weights = weights / total_abs * np.sum(np.abs(deltas))
        return {a: float(w) for a, w in zip(assets, weights)}
    except Exception:
        # Fallback: proportional to delta
        return {a: -exposures[a]['delta'] for a in assets}

# --- Optional: Telegram command handler stub ---
def format_hedge_portfolio_message(hedge_alloc: dict) -> str:
    msg = "\U0001F4B8 Portfolio Hedge Suggestion:\n"
    for asset, size in hedge_alloc.items():
        msg += f"{asset}: {size:+.4f}\n"
    return msg
