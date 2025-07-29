from datetime import datetime, timedelta

def select_option(option_chain, type, moneyness="ATM", days_to_expiry=7):
    """
    Select an option from the chain by type, moneyness, and expiry window.
    moneyness: 'ATM', 'OTM', 'ITM'
    """
    now = datetime.utcnow()
    filtered = [o for o in option_chain if o['type'] == type]
    # Expiry filter
    filtered = [o for o in filtered if abs((datetime.strptime(o['expiry'], "%Y-%m-%d") - now).days) <= days_to_expiry]
    if not filtered:
        return None
    # Moneyness filter
    if moneyness == "ATM":
        filtered = sorted(filtered, key=lambda x: abs(x['strike'] - x.get('spot', 0)))
    elif moneyness == "OTM":
        if type == 'put':
            filtered = [o for o in filtered if o['strike'] < o.get('spot', 0)]
        else:
            filtered = [o for o in filtered if o['strike'] > o.get('spot', 0)]
    elif moneyness == "ITM":
        if type == 'put':
            filtered = [o for o in filtered if o['strike'] > o.get('spot', 0)]
        else:
            filtered = [o for o in filtered if o['strike'] < o.get('spot', 0)]
    if not filtered:
        return None
    # Closest to ATM or OTM
    return min(filtered, key=lambda x: abs(x['strike'] - x.get('spot', 0)))

def hedge_with_protective_put(asset, spot_price, portfolio_delta, option_chain):
    # Attach spot to each option for moneyness
    for o in option_chain:
        o['spot'] = spot_price
    put = select_option(option_chain, 'put', moneyness="OTM", days_to_expiry=14)
    if not put:
        return {'action': 'no_put_found'}
    contracts = abs(portfolio_delta) / abs(put['delta']) if put['delta'] else 1
    return {
        'action': 'buy_put',
        'strike': put['strike'],
        'expiry': put['expiry'],
        'contracts': round(contracts, 2),
        'option': put
    }

def hedge_with_covered_call(asset, spot_price, holdings, option_chain):
    for o in option_chain:
        o['spot'] = spot_price
    call = select_option(option_chain, 'call', moneyness="OTM", days_to_expiry=14)
    if not call:
        return {'action': 'no_call_found'}
    contracts = abs(holdings) / abs(call['delta']) if call['delta'] else 1
    return {
        'action': 'sell_call',
        'strike': call['strike'],
        'expiry': call['expiry'],
        'contracts': round(contracts, 2),
        'option': call
    }

def hedge_with_collar(asset, spot_price, holdings, option_chain):
    for o in option_chain:
        o['spot'] = spot_price
    put = select_option(option_chain, 'put', moneyness="OTM", days_to_expiry=14)
    call = select_option(option_chain, 'call', moneyness="OTM", days_to_expiry=14)
    if not put or not call:
        return {'action': 'no_collar_found'}
    put_contracts = abs(holdings) / abs(put['delta']) if put['delta'] else 1
    call_contracts = abs(holdings) / abs(call['delta']) if call['delta'] else 1
    return {
        'action': 'collar',
        'put_strike': put['strike'],
        'call_strike': call['strike'],
        'expiry': put['expiry'],
        'put_contracts': round(put_contracts, 2),
        'call_contracts': round(call_contracts, 2),
        'put_option': put,
        'call_option': call
    }

def select_hedging_strategy(strategy_name, asset, spot, delta, option_chain):
    if strategy_name == 'protective_put':
        return hedge_with_protective_put(asset, spot, delta, option_chain)
    elif strategy_name == 'covered_call':
        return hedge_with_covered_call(asset, spot, delta, option_chain)
    elif strategy_name == 'collar':
        return hedge_with_collar(asset, spot, delta, option_chain)
    else:
        return {'action': 'unknown_strategy'}

# --- Unit Tests ---
def _unit_test():
    mock_chain = [
        {'type': 'put', 'strike': 31000, 'expiry': '2024-07-20', 'delta': -0.45, 'price': 320, 'iv': 0.57},
        {'type': 'put', 'strike': 30000, 'expiry': '2024-07-20', 'delta': -0.5, 'price': 250, 'iv': 0.6},
        {'type': 'call', 'strike': 33000, 'expiry': '2024-07-20', 'delta': 0.4, 'price': 210, 'iv': 0.55},
        {'type': 'call', 'strike': 34000, 'expiry': '2024-07-20', 'delta': 0.3, 'price': 150, 'iv': 0.5}
    ]
    spot = 31000
    delta = -1.2
    holdings = 1.2
    print('Protective Put:', hedge_with_protective_put('BTC', spot, delta, mock_chain))
    print('Covered Call:', hedge_with_covered_call('BTC', spot, holdings, mock_chain))
    print('Collar:', hedge_with_collar('BTC', spot, holdings, mock_chain))
    print('Router (put):', select_hedging_strategy('protective_put', 'BTC', spot, delta, mock_chain))
    print('Router (call):', select_hedging_strategy('covered_call', 'BTC', spot, holdings, mock_chain))
    print('Router (collar):', select_hedging_strategy('collar', 'BTC', spot, holdings, mock_chain))

if __name__ == "__main__":
    _unit_test()
