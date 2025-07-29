import os
from config import HEDGE_STRATEGY, AUTO_EXECUTE, HEDGE_SLIPPAGE_BPS
from exchange_api.okx import fetch_order_book as okx_order_book
from exchange_api.bybit import fetch_order_book as bybit_order_book
from exchange_api.deribit import fetch_order_book as deribit_order_book, fetch_futures_price, fetch_spot_price
from risk_engine.risk_metrics import calculate_delta
from analytics.reporting import log_hedge_execution
import datetime

class StrategyEngine:
    def __init__(self, logger=None):
        self.logger = logger

    def delta_neutral_hedge(self, spot_position_size, asset_beta=1.0):
        """Calculate delta-neutral hedge size for perpetuals."""
        hedge_size = -spot_position_size * asset_beta
        return hedge_size

    def options_based_hedge(self, spot_position_size, option_chain, strategy='protective_put', risk_threshold=0.2):
        """
        Compute optimal option hedge (protective put, covered call, collar).
        Returns dict with strike, expiry, contracts, cost.
        """
        # For simplicity, pick ATM option with nearest expiry
        atm_option = min(option_chain, key=lambda o: abs(o['strike'] - o['spot']))
        contracts = abs(spot_position_size) / abs(atm_option.get('delta', 1))
        cost = contracts * atm_option['price']
        return {
            'strategy': strategy,
            'strike': atm_option['strike'],
            'expiry': atm_option['expiry'],
            'contracts': contracts,
            'cost': cost
        }

    def execute_hedge(self, asset, size, type='perpetual', auto_execute=None):
        """
        Simulate smart order routing and execution for perpetual or option hedge.
        """
        auto_execute = AUTO_EXECUTE if auto_execute is None else auto_execute
        # Fetch order books
        ob_okx = okx_order_book(asset)
        ob_bybit = bybit_order_book(asset)
        ob_deribit = deribit_order_book(asset)
        # Pick best price
        if size < 0:
            # Sell: pick highest bid
            best = max([
                ('OKX', ob_okx['bids'][0][0]),
                ('Bybit', ob_bybit['bids'][0][0]),
                ('Deribit', ob_deribit['bids'][0][0])
            ], key=lambda x: x[1])
        else:
            # Buy: pick lowest ask
            best = min([
                ('OKX', ob_okx['asks'][0][0]),
                ('Bybit', ob_bybit['asks'][0][0]),
                ('Deribit', ob_deribit['asks'][0][0])
            ], key=lambda x: x[1])
        price = best[1]
        exchange = best[0]
        slippage = abs(size) * price * (HEDGE_SLIPPAGE_BPS / 10000)
        cost = abs(size) * price + slippage
        timestamp = datetime.datetime.utcnow().isoformat()
        details = {
            'asset': asset,
            'size': size,
            'price': price,
            'cost': cost,
            'timestamp': timestamp,
            'strategy': type,
            'status': 'pending' if not auto_execute else 'success'
        }
        log_hedge_execution(details)
        if self.logger:
            self.logger.info(f"Hedge recommendation: {details}")
        if not auto_execute:
            return {'recommendation': details, 'exchange': exchange}
        # Simulate execution
        details['status'] = 'success'
        log_hedge_execution(details)
        return {'executed': details, 'exchange': exchange}

    def confirm_and_execute(self, asset, size, type='perpetual'):
        # This would be called after Telegram confirmation
        return self.execute_hedge(asset, size, type, auto_execute=True)
