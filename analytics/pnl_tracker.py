def calculate_position_pnl(entry_price: float, current_price: float, size: float, direction: str) -> float:
    """
    Calculate realized/unrealized P&L for a position.
    direction: 'long' or 'short'
    """
    if direction == 'long':
        return (current_price - entry_price) * size
    elif direction == 'short':
        return (entry_price - current_price) * size
    else:
        raise ValueError('direction must be "long" or "short"')

def calculate_hedge_effectiveness(spot_pnl: float, hedge_pnl: float) -> float:
    """
    Compute hedge effectiveness ratio = hedge_pnl / total_pnl
    Tag scenarios where hedge worsened losses or over-hedged
    """
    total_pnl = spot_pnl + hedge_pnl
    if total_pnl == 0:
        return 0.0
    return (hedge_pnl / total_pnl) * 100

def compute_portfolio_pnl(portfolio: list, market_prices: dict) -> dict:
    spot_pnl = 0
    hedge_pnl = 0
    for pos in portfolio:
        symbol = pos['symbol']
        typ = pos['type']
        entry = pos['entry_price']
        curr = pos.get('current_price', market_prices.get(symbol, entry))
        size = pos['size']
        direction = pos['direction']
        pnl = calculate_position_pnl(entry, curr, size, direction)
        if typ == 'spot':
            spot_pnl += pnl
        else:
            hedge_pnl += pnl
    total_pnl = spot_pnl + hedge_pnl
    effectiveness = calculate_hedge_effectiveness(spot_pnl, hedge_pnl)
    return {
        'total_pnl': total_pnl,
        'spot_pnl': spot_pnl,
        'hedge_pnl': hedge_pnl,
        'hedge_effectiveness': effectiveness
    }

def format_pnl_report(asset: str, pnl_dict: dict) -> str:
    eff = pnl_dict['hedge_effectiveness']
    eff_tag = '✅' if eff > 0 else '⚠️'
    return (f"\U0001F4B0 P&L Report for {asset}:\n"
            f"Spot P&L: {pnl_dict['spot_pnl']:+.0f}\n"
            f"Hedge P&L: {pnl_dict['hedge_pnl']:+.0f}\n"
            f"Effectiveness: {eff:.1f}% {eff_tag}")

# --- Unit Tests ---
def _unit_test():
    # Up market, long spot, short perp
    portfolio = [
        {'symbol': 'BTC', 'type': 'spot', 'entry_price': 27000, 'current_price': 28000, 'size': 1, 'direction': 'long'},
        {'symbol': 'BTC-PERP', 'type': 'perp', 'entry_price': 27000, 'current_price': 28000, 'size': 1, 'direction': 'short'}
    ]
    market = {'BTC': 28000, 'BTC-PERP': 28000}
    res = compute_portfolio_pnl(portfolio, market)
    print('Up market:', res)
    # Down market, long spot, long put
    portfolio2 = [
        {'symbol': 'BTC', 'type': 'spot', 'entry_price': 27000, 'current_price': 26000, 'size': 1, 'direction': 'long'},
        {'symbol': 'BTC-30JUL24-25000P', 'type': 'option', 'entry_price': 500, 'current_price': 800, 'size': 1, 'direction': 'long'}
    ]
    market2 = {'BTC': 26000, 'BTC-30JUL24-25000P': 800}
    res2 = compute_portfolio_pnl(portfolio2, market2)
    print('Down market:', res2)
    # Over-hedged
    portfolio3 = [
        {'symbol': 'BTC', 'type': 'spot', 'entry_price': 27000, 'current_price': 26000, 'size': 1, 'direction': 'long'},
        {'symbol': 'BTC-PERP', 'type': 'perp', 'entry_price': 27000, 'current_price': 26000, 'size': 2, 'direction': 'short'}
    ]
    market3 = {'BTC': 26000, 'BTC-PERP': 26000}
    res3 = compute_portfolio_pnl(portfolio3, market3)
    print('Over-hedged:', res3)
    # Format report
    print(format_pnl_report('BTC', res))
    print(format_pnl_report('BTC', res2))
    print(format_pnl_report('BTC', res3))

if __name__ == "__main__":
    _unit_test()
