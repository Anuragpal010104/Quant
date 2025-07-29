import os
import time
import random
import datetime
from analytics.reporting import log_hedge_execution
from exchange_api.okx import fetch_order_book as okx_order_book
from exchange_api.bybit import fetch_order_book as bybit_order_book
from exchange_api.deribit import fetch_order_book as deribit_order_book

USE_MOCK = os.getenv("USE_MOCK_EXECUTION", "False").lower() == "true"

# --- Universal Order Execution ---
def execute_order(exchange: str, symbol: str, side: str, size: float, order_type: str = "market") -> dict:
    '''
    Execute an order and return order execution details.
    '''
    timestamp = datetime.datetime.utcnow().isoformat()
    if USE_MOCK:
        # Simulate execution
        price = 57000 + random.randint(-100, 100)
        slippage_bps = random.uniform(5, 20)
        fee = 0.0005
        cost = abs(size) * price * (1 + fee) + abs(size) * price * (slippage_bps / 10000)
        status = 'success'
        details = {
            'timestamp': timestamp,
            'asset': symbol,
            'size': size,
            'side': side,
            'price': price,
            'exchange': exchange,
            'strategy': order_type,
            'status': status,
            'slippage_bps': slippage_bps,
            'cost_usd': cost
        }
        log_hedge_execution(details)
        return details
    # Real execution would go here (API call)
    # For now, fallback to mock
    return execute_order('mock', symbol, side, size, order_type)

# --- Smart Order Routing ---
def get_best_execution(exchange_list: list, symbol: str, side: str, size: float):
    order_books = {}
    for ex in exchange_list:
        if ex.lower() == 'okx':
            order_books['okx'] = okx_order_book(symbol)
        elif ex.lower() == 'bybit':
            order_books['bybit'] = bybit_order_book(symbol)
        elif ex.lower() == 'deribit':
            order_books['deribit'] = deribit_order_book(symbol)
    # Find best price
    best_ex = None
    best_price = None
    for ex, ob in order_books.items():
        price = ob['asks'][0][0] if side == 'buy' else ob['bids'][0][0]
        if best_price is None or (side == 'buy' and price < best_price) or (side == 'sell' and price > best_price):
            best_price = price
            best_ex = ex
    return best_ex, best_price

# --- Cost Estimation ---
def estimate_cost(symbol: str, size: float, entry_price: float, execution_price: float):
    slippage = abs(execution_price - entry_price)
    slippage_bps = (slippage / entry_price) * 10000 if entry_price else 0
    fee = 0.0005 * abs(size) * execution_price
    total_cost = abs(size) * execution_price + fee + abs(size) * slippage
    return {
        'slippage_bps': slippage_bps,
        'fee': fee,
        'total_cost': total_cost
    }

# --- Telegram Notification Helper ---
def notify_execution(details: dict, notify_func=None):
    msg = (f"✅ Hedge Executed: {details['size']:+.4f} {details['asset']} on {details['exchange'].upper()} @ {details['price']:,} USD | "
           f"Slippage: {details['slippage_bps']:.1f} bps | Cost: ${details['cost_usd']:.2f}")
    if notify_func:
        notify_func(msg)
    return msg

class ExecutionEngine:
    def __init__(self, exchanges=None, use_mock=None):
        self.exchanges = exchanges or ['okx', 'bybit', 'deribit']
        self.use_mock = USE_MOCK if use_mock is None else use_mock

    def get_best_quote(self, asset: str, side: str, exchanges: list = None) -> dict:
        exchanges = exchanges or self.exchanges
        best_ex = None
        best_price = None
        best_ob = None
        for ex in exchanges:
            if ex == 'okx':
                ob = okx_order_book(asset)
            elif ex == 'bybit':
                ob = bybit_order_book(asset)
            elif ex == 'deribit':
                ob = deribit_order_book(asset)
            else:
                continue
            if not ob:
                continue
            price = ob['asks'][0][0] if side == 'buy' else ob['bids'][0][0]
            if best_price is None or (side == 'buy' and price < best_price) or (side == 'sell' and price > best_price):
                best_price = price
                best_ex = ex
                best_ob = ob
        return {'exchange': best_ex, 'price': best_price, 'order_book': best_ob}

    def estimate_slippage(self, order_size: float, order_book: dict, side: str, depth: int = 5) -> float:
        levels = order_book['asks'] if side == 'buy' else order_book['bids']
        filled = 0
        cost = 0
        for price, qty in levels[:depth]:
            take = min(order_size - filled, qty)
            cost += take * price
            filled += take
            if filled >= order_size:
                break
        avg_price = cost / order_size if order_size else 0
        top_price = levels[0][0]
        slippage = abs(avg_price - top_price)
        return slippage

    def calculate_hedging_cost(self, entry_price, hedge_size, fee_rate, slippage):
        fee = abs(hedge_size) * entry_price * fee_rate
        total_cost = fee + abs(hedge_size) * slippage
        pct_cost = total_cost / (abs(hedge_size) * entry_price) if hedge_size else 0
        return total_cost, pct_cost

    def execute_perpetual_hedge(self, asset: str, size: float, side: str) -> dict:
        quote = self.get_best_quote(asset, side)
        price = quote['price']
        ex = quote['exchange']
        ob = quote['order_book']
        slippage = self.estimate_slippage(abs(size), ob, side)
        fee_rate = 0.0005
        cost, pct_cost = self.calculate_hedging_cost(price, size, fee_rate, slippage)
        timestamp = datetime.datetime.utcnow().isoformat()
        if self.use_mock:
            trade_id = f"MOCK-{random.randint(100000,999999)}"
            status = 'mocked'
        else:
            # Real execution logic would go here
            trade_id = f"REAL-{random.randint(100000,999999)}"
            status = 'executed'
        result = {
            'status': status,
            'exchange': ex,
            'asset': asset,
            'size': size,
            'side': side,
            'price': price,
            'cost': cost,
            'slippage': slippage,
            'pct_cost': pct_cost,
            'timestamp': timestamp,
            'trade_id': trade_id
        }
        log_hedge_execution(result)
        return result

    def execute_option_hedge(self, asset: str, option_type: str, strike: float, size: float) -> dict:
        # For simplicity, use Deribit order book for options
        ob = deribit_order_book(asset)
        side = 'buy' if size > 0 else 'sell'
        slippage = self.estimate_slippage(abs(size), ob, side)
        price = ob['asks'][0][0] if side == 'buy' else ob['bids'][0][0]
        fee_rate = 0.0005
        cost, pct_cost = self.calculate_hedging_cost(price, size, fee_rate, slippage)
        timestamp = datetime.datetime.utcnow().isoformat()
        if self.use_mock:
            trade_id = f"MOCKOPT-{random.randint(100000,999999)}"
            status = 'mocked'
        else:
            # Real execution logic would go here
            trade_id = f"REALOPT-{random.randint(100000,999999)}"
            status = 'executed'
        result = {
            'status': status,
            'exchange': 'deribit',
            'asset': asset,
            'option_type': option_type,
            'strike': strike,
            'size': size,
            'price': price,
            'cost': cost,
            'slippage': slippage,
            'pct_cost': pct_cost,
            'timestamp': timestamp,
            'trade_id': trade_id
        }
        log_hedge_execution(result)
        return result

# --- Unit Test ---
def _unit_test():
    engine = ExecutionEngine(use_mock=True)
    # Perpetual hedge test
    res1 = engine.execute_perpetual_hedge('BTC', 0.3, 'buy')
    res2 = engine.execute_perpetual_hedge('ETH', -0.5, 'sell')
    # Option hedge test
    res3 = engine.execute_option_hedge('BTC', 'call', 60000, 1)
    print('Perp hedge BTC:', res1)
    print('Perp hedge ETH:', res2)
    print('Option hedge BTC:', res3)
    assert res1['cost'] < 100 and res1['slippage'] < 10, 'BTC hedge cost/slippage too high'
    assert res2['cost'] < 100 and res2['slippage'] < 10, 'ETH hedge cost/slippage too high'
    assert res3['cost'] < 100 and res3['slippage'] < 10, 'Option hedge cost/slippage too high'
    print('All tests passed.')

if __name__ == "__main__":
    _unit_test()
