import numpy as np
import pandas as pd
from scipy.stats import linregress
from typing import List, Dict

def calculate_portfolio_delta(positions: List[Dict]) -> float:
    return sum(p.get('delta', 0) * p.get('size', 1) for p in positions)

def calculate_portfolio_greeks(positions: List[Dict]) -> Dict[str, float]:
    total = {'delta': 0, 'gamma': 0, 'vega': 0, 'theta': 0}
    for p in positions:
        for greek in total:
            total[greek] += p.get(greek, 0) * p.get('size', 1)
    return total

def calculate_portfolio_var(price_history: np.ndarray, weights: np.ndarray, confidence: float = 0.95) -> float:
    returns = np.diff(np.log(price_history), axis=0)
    port_returns = returns @ weights
    mean = np.mean(port_returns)
    std = np.std(port_returns)
    var = abs(np.percentile(port_returns, (1-confidence)*100))
    return var

def calculate_max_drawdown(price_series: List[float]) -> float:
    arr = np.array(price_series)
    roll_max = np.maximum.accumulate(arr)
    drawdown = (arr - roll_max) / roll_max
    return abs(drawdown.min())

def calculate_pnl_attribution(positions: List[Dict], current_prices: Dict[str, float]) -> Dict[str, float]:
    pnl = {}
    for p in positions:
        symbol = p['instrument_name']
        entry = p.get('entry_price', current_prices.get(symbol, 0))
        exit = current_prices.get(symbol, entry)
        size = p.get('size', 1)
        side = p.get('side', 'buy')
        pnl[symbol] = (exit - entry) * size if side == 'buy' else (entry - exit) * size
    return pnl

def calculate_asset_correlation(price_dict: Dict[str, List[float]]) -> pd.DataFrame:
    df = pd.DataFrame(price_dict)
    return df.pct_change().corr()

def calculate_beta(asset_returns: np.ndarray, benchmark_returns: np.ndarray) -> float:
    slope, _, _, _, _ = linregress(benchmark_returns, asset_returns)
    return slope

def simulate_market_shock(positions: List[Dict], price_drop: float) -> Dict:
    shocked = []
    for p in positions:
        shocked_price = p['S'] * (1 + price_drop)
        shocked_pos = p.copy()
        shocked_pos['S'] = shocked_price
        shocked.append(shocked_pos)
    # Recalculate greeks (assume functions available)
    # For demo, just return shocked positions
    return {'shocked_positions': shocked}

def calculate_realized_pnl(entry_price, exit_price, size, side):
    if side == 'buy':
        return (exit_price - entry_price) * size
    else:
        return (entry_price - exit_price) * size

def get_hedging_costs_from_log(file_path: str) -> float:
    import csv
    total_cost = 0
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_cost += float(row.get('cost', 0))
    return total_cost
