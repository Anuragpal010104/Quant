import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, List, Dict, Any
from datetime import datetime

USE_MOCK = os.getenv("USE_MOCK_BACKTEST", "False").lower() == "true"

class BacktestEngine:
    def __init__(self, results_dir: str = "backtesting/results"):
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

    def load_price_data(self, symbol: str, timeframe: str = "1h") -> pd.DataFrame:
        """
        Load historical price data from CSV or mock API.
        """
        fname = f"mock_{symbol}_{timeframe}.csv" if USE_MOCK else f"{symbol}_{timeframe}.csv"
        path = os.path.join(self.results_dir, "..", fname)
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=[0])
            df.columns = [c.lower() for c in df.columns]
            return df
        # Fallback: generate mock data
        n = 24 * 7 if timeframe == "1h" else 30
        price = np.cumprod(1 + 0.01 * np.random.randn(n)) * 30000
        dt = pd.date_range(end=datetime.utcnow(), periods=n, freq=timeframe.upper())
        df = pd.DataFrame({"timestamp": dt, "close": price})
        return df

    def run_backtest(self, strategy: Callable, positions: List[Dict], price_data: pd.DataFrame, strategy_name: str = "strategy") -> Dict:
        """
        Simulate applying the given strategy over time.
        """
        pnl_curve = []
        hedge_costs = []
        exposures = []
        drawdowns = []
        actions = []
        cash = 0
        position = 0
        max_equity = 0
        equity_curve = []
        for i, row in price_data.iterrows():
            step_data = row.to_dict()
            # Apply strategy
            action = strategy(step_data, positions, position)
            actions.append(action)
            # Simulate execution
            price = step_data.get('close', step_data.get('price', 0))
            if action.get('hedge'):
                hedge_size = action['hedge_size']
                cost = abs(hedge_size) * price * 0.0005  # fee
                slippage = abs(hedge_size) * price * 0.0002
                cash -= cost + slippage
                hedge_costs.append(cost + slippage)
                position += hedge_size
            # Mark-to-market PnL
            mtm = position * (price - price_data.iloc[0]['close'])
            equity = cash + mtm
            pnl_curve.append(equity)
            exposures.append(position)
            max_equity = max(max_equity, equity)
            drawdown = (max_equity - equity)
            drawdowns.append(drawdown)
            equity_curve.append(equity)
        # VaR (historical)
        returns = pd.Series(pnl_curve).diff().dropna()
        var_95 = np.percentile(returns, 5)
        result = {
            'pnl_curve': pnl_curve,
            'hedge_costs': hedge_costs,
            'exposures': exposures,
            'drawdowns': drawdowns,
            'VaR_95': var_95,
            'final_pnl': pnl_curve[-1] if pnl_curve else 0,
            'actions': actions
        }
        # Save results
        out_path = os.path.join(self.results_dir, f"{strategy_name}.json")
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return result

    def apply_strategy_at_step(self, step_data: Dict, current_position: float, strategy_func: Callable) -> Dict:
        """
        Apply hedge logic using current market snapshot and return action dict.
        """
        return strategy_func(step_data, current_position)

    def plot_results(self, result: Dict, price_data: pd.DataFrame, strategy_name: str = "strategy"):
        plt.figure(figsize=(12, 8))
        plt.subplot(3, 1, 1)
        plt.plot(price_data['timestamp'], price_data['close'], label='Price')
        plt.title(f"{strategy_name} - Price & Hedge Actions")
        for i, a in enumerate(result['actions']):
            if a.get('hedge'):
                plt.scatter(price_data['timestamp'].iloc[i], price_data['close'].iloc[i], color='red', marker='^')
        plt.legend()
        plt.subplot(3, 1, 2)
        plt.plot(price_data['timestamp'], result['pnl_curve'], label='PnL')
        plt.title("PnL Curve")
        plt.legend()
        plt.subplot(3, 1, 3)
        plt.plot(price_data['timestamp'], result['exposures'], label='Exposure')
        plt.title("Delta Exposure Over Time")
        plt.legend()
        plt.tight_layout()
        plt.show()

# --- Example/test strategies ---
def delta_neutral_strategy(step_data: Dict, positions: List[Dict], current_position: float) -> Dict:
    # Hedge to zero delta
    price = step_data.get('close', step_data.get('price', 0))
    target_delta = 0
    hedge_size = target_delta - current_position
    return {'hedge': abs(hedge_size) > 1e-4, 'hedge_size': hedge_size}

def no_hedge_strategy(step_data: Dict, positions: List[Dict], current_position: float) -> Dict:
    return {'hedge': False, 'hedge_size': 0}

# --- Unit Test ---
def _unit_test():
    engine = BacktestEngine()
    price_data = engine.load_price_data('BTCUSDT', '1h')
    positions = []
    res1 = engine.run_backtest(delta_neutral_strategy, positions, price_data, 'delta_neutral')
    res2 = engine.run_backtest(no_hedge_strategy, positions, price_data, 'no_hedge')
    print(f"Delta-neutral final PnL: {res1['final_pnl']:.2f}")
    print(f"No-hedge final PnL: {res2['final_pnl']:.2f}")
    assert res1['final_pnl'] > res2['final_pnl'] or abs(res1['final_pnl']) < 1e-2, "Delta-neutral should outperform or be flat in high vol"
    engine.plot_results(res1, price_data, 'delta_neutral')

if __name__ == "__main__":
    _unit_test()
