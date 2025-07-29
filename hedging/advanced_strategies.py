import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

def option_payoff(S, K, type, position, premium=0):
    if type == 'call':
        return position * (np.maximum(S - K, 0) - premium)
    else:
        return position * (np.maximum(K - S, 0) - premium)

def construct_iron_condor(S, K_center, width, T, r, sigma):
    legs = [
        {'type': 'call', 'K': K_center + width, 'position': -1},  # Sell OTM call
        {'type': 'call', 'K': K_center + 2*width, 'position': 1}, # Buy further OTM call
        {'type': 'put', 'K': K_center - width, 'position': -1},   # Sell OTM put
        {'type': 'put', 'K': K_center - 2*width, 'position': 1},  # Buy further OTM put
    ]
    # Calculate premiums using Black-Scholes
    for leg in legs:
        d1 = (np.log(S / leg['K']) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if leg['type'] == 'call':
            price = S * norm.cdf(d1) - leg['K'] * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = leg['K'] * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        leg['premium'] = price
    return legs

def construct_butterfly_spread(S, K_center, width, T, r, sigma, type='call'):
    legs = [
        {'type': type, 'K': K_center - width, 'position': 1},
        {'type': type, 'K': K_center, 'position': -2},
        {'type': type, 'K': K_center + width, 'position': 1},
    ]
    for leg in legs:
        d1 = (np.log(S / leg['K']) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if leg['type'] == 'call':
            price = S * norm.cdf(d1) - leg['K'] * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = leg['K'] * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        leg['premium'] = price
    return legs

def construct_straddle(S, K, T, r, sigma):
    legs = [
        {'type': 'call', 'K': K, 'position': 1},
        {'type': 'put', 'K': K, 'position': 1},
    ]
    for leg in legs:
        d1 = (np.log(S / leg['K']) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if leg['type'] == 'call':
            price = S * norm.cdf(d1) - leg['K'] * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = leg['K'] * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        leg['premium'] = price
    return legs

def evaluate_strategy_payoff(strategy, price_range):
    payoff = np.zeros_like(price_range, dtype=float)
    for leg in strategy:
        payoff += option_payoff(price_range, leg['K'], leg['type'], leg['position'], leg['premium'])
    return payoff

def plot_payoff(price_range, payoff, title='Strategy Payoff'):
    plt.figure(figsize=(8,4))
    plt.plot(price_range, payoff, label='Payoff')
    plt.axhline(0, color='gray', linestyle='--')
    plt.title(title)
    plt.xlabel('Underlying Price at Expiry')
    plt.ylabel('P&L')
    plt.legend()
    plt.tight_layout()
    plt.show()

# --- Unit Test ---
def _unit_test():
    S = 100
    K = 100
    width = 10
    T = 0.1
    r = 0.01
    sigma = 0.5
    price_range = np.linspace(60, 140, 200)
    iron_condor = construct_iron_condor(S, K, width, T, r, sigma)
    butterfly = construct_butterfly_spread(S, K, width, T, r, sigma, 'call')
    straddle = construct_straddle(S, K, T, r, sigma)
    payoff_ic = evaluate_strategy_payoff(iron_condor, price_range)
    payoff_bf = evaluate_strategy_payoff(butterfly, price_range)
    payoff_straddle = evaluate_strategy_payoff(straddle, price_range)
    print('Iron Condor legs:', iron_condor)
    print('Butterfly legs:', butterfly)
    print('Straddle legs:', straddle)
    plot_payoff(price_range, payoff_ic, 'Iron Condor Payoff')
    plot_payoff(price_range, payoff_bf, 'Butterfly Spread Payoff')
    plot_payoff(price_range, payoff_straddle, 'Straddle Payoff')

if __name__ == "__main__":
    _unit_test()
