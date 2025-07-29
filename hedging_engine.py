import math
from typing import Dict, Any, Tuple

class HedgingEngine:
    def __init__(self, okx_client=None, bybit_client=None, deribit_client=None, logger=None):
        self.okx = okx_client
        self.bybit = bybit_client
        self.deribit = deribit_client
        self.logger = logger

    def compute_optimal_hedge_size(self, position: dict, market_data: dict, strategy: str = "perpetual", risk_reduction: float = 1.0) -> float:
        """
        Compute hedge size for perpetual or options-based hedging.
        risk_reduction: 1.0 = full hedge, 0.5 = 50% hedge, etc.
        """
        if strategy == "perpetual":
            # Use delta for spot/options, beta for portfolio
            delta = position.get("delta", 0)
            hedge_size = -delta * risk_reduction
            return hedge_size
        elif strategy == "option":
            # Delta-neutral: contracts needed = position delta / option delta
            pos_delta = position.get("delta", 0)
            option_delta = market_data.get("option_delta", 1)
            contracts = -pos_delta / option_delta * risk_reduction if option_delta else 0
            return contracts
        else:
            raise ValueError("Unknown hedging strategy")

    def estimate_execution_cost(self, symbol: str, side: str, size: float, exchange: str, order_book: dict = None) -> float:
        """
        Estimate cost using order book depth, fees, and price impact.
        """
        if not order_book:
            return 0.0
        price = order_book['asks'][0][0] if side == 'buy' else order_book['bids'][0][0]
        # Simple slippage: assume linear impact for small size
        depth = sum([lvl[1] for lvl in (order_book['asks'] if side == 'buy' else order_book['bids'])])
        slippage = 0.001 * abs(size) if depth > 0 else 0
        fee_rate = 0.0005  # 0.05% typical taker fee
        cost = abs(size) * price * (1 + fee_rate) + slippage * price
        return cost

    def route_order(self, symbol: str, side: str, size: float) -> Tuple[str, str]:
        """
        Select best exchange based on estimated cost. Returns (exchange, fallback_exchange)
        """
        # Mock order books
        ob_okx = {'bids': [[57000, 10]], 'asks': [[57100, 10]]}
        ob_bybit = {'bids': [[56990, 10]], 'asks': [[57110, 10]]}
        ob_deribit = {'bids': [[57010, 10]], 'asks': [[57120, 10]]}
        costs = {
            'OKX': self.estimate_execution_cost(symbol, side, size, 'OKX', ob_okx),
            'Bybit': self.estimate_execution_cost(symbol, side, size, 'Bybit', ob_bybit),
            'Deribit': self.estimate_execution_cost(symbol, side, size, 'Deribit', ob_deribit)
        }
        sorted_ex = sorted(costs.items(), key=lambda x: x[1])
        return sorted_ex[0][0], sorted_ex[1][0]

    def execute_hedge(self, strategy: str, asset: str, size: float, side: str = None, notify=None) -> Dict[str, Any]:
        """
        Place a mock or real hedge order. Calls notify callback if provided.
        """
        exchange, fallback = self.route_order(asset, side or ("sell" if size < 0 else "buy"), abs(size))
        # Mock execution
        order_response = {
            'exchange': exchange,
            'asset': asset,
            'size': size,
            'side': side or ("sell" if size < 0 else "buy"),
            'status': 'success',
            'cost': abs(size) * 57000,
            'fallback': fallback
        }
        if self.logger:
            self.logger.info(f"Hedge order: {order_response}")
        if notify:
            msg = (f"Hedge order placed on {exchange}: {size:.4f} {asset} ({order_response['side']})\n"
                   f"Estimated cost: ${order_response['cost']:.2f}\nStatus: {order_response['status']}")
            notify(msg)
        return order_response
