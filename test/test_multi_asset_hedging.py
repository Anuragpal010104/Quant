import pandas as pd
import numpy as np
from portfolio.multi_asset_hedging import (
    calculate_cross_asset_correlation,
    compute_portfolio_exposure,
    optimal_hedge_allocation
)

def test_correlation():
    price_data = {
        'BTC': [10000, 10100, 10200, 10150, 10300],
        'ETH': [200, 202, 204, 203, 207]
    }
    corr = calculate_cross_asset_correlation(price_data)
    print('Correlation matrix:\n', corr)
    assert corr.shape == (2, 2)

def test_exposure():
    positions = [
        {'symbol': 'BTC', 'delta': 1.2, 'gamma': 0.1, 'vega': 0.2, 'theta': -0.01},
        {'symbol': 'ETH', 'delta': -0.5, 'gamma': 0.05, 'vega': 0.1, 'theta': -0.005},
        {'symbol': 'BTC', 'delta': -0.7, 'gamma': 0.02, 'vega': 0.05, 'theta': -0.002}
    ]
    exposures = compute_portfolio_exposure(positions)
    print('Exposures:', exposures)
    assert abs(exposures['BTC']['delta'] - 0.5) < 1e-6
    assert abs(exposures['ETH']['delta'] + 0.5) < 1e-6

def test_optimal_hedge():
    exposures = {
        'BTC': {'delta': 0.5, 'gamma': 0, 'vega': 0, 'theta': 0},
        'ETH': {'delta': -0.5, 'gamma': 0, 'vega': 0, 'theta': 0}
    }
    corr = pd.DataFrame([[1, 0.8], [0.8, 1]], columns=['BTC', 'ETH'], index=['BTC', 'ETH'])
    alloc = optimal_hedge_allocation(exposures, corr)
    print('Hedge allocation:', alloc)
    assert 'BTC' in alloc and 'ETH' in alloc

if __name__ == "__main__":
    test_correlation()
    test_exposure()
    test_optimal_hedge()
    print('All multi-asset hedging tests passed.')
