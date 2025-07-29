import pandas as pd
import numpy as np

def calculate_hedging_costs(hedge_logs: pd.DataFrame) -> float:
    """
    Sum of all hedge execution costs (USD).
    """
    return hedge_logs['cost'].sum() if 'cost' in hedge_logs else 0.0

def calculate_hedge_effectiveness(pnl_series: list, hedged_pnl_series: list) -> dict:
    """
    Compare PnL before/after hedging. Output: % risk reduction, cost vs benefit.
    """
    pnl = np.array(pnl_series)
    hedged = np.array(hedged_pnl_series)
    vol_before = np.std(pnl)
    vol_after = np.std(hedged)
    risk_reduction = 100 * (vol_before - vol_after) / vol_before if vol_before else 0
    benefit = np.mean(hedged) - np.mean(pnl)
    return {
        'risk_reduction_pct': risk_reduction,
        'mean_benefit': benefit,
        'vol_before': vol_before,
        'vol_after': vol_after
    }

def generate_performance_report(hedge_logs: pd.DataFrame, pnl_data: dict) -> str:
    freq = len(hedge_logs)
    total_cost = calculate_hedging_costs(hedge_logs)
    effectiveness = calculate_hedge_effectiveness(pnl_data['pnl'], pnl_data['hedged_pnl'])
    report = [
        f"\U0001F4C9 <b>Hedge Performance Report</b>",
        f"Hedge Frequency: <b>{freq}</b>",
        f"Total Hedging Cost: <b>${total_cost:,.2f}</b>",
        f"Risk Reduction: <b>{effectiveness['risk_reduction_pct']:.1f}%</b>",
        f"Mean Benefit: <b>${effectiveness['mean_benefit']:.2f}</b>",
        f"Volatility Before: <b>{effectiveness['vol_before']:.2f}</b>",
        f"Volatility After: <b>{effectiveness['vol_after']:.2f}</b>"
    ]
    return "\n".join(report)

# --- Unit Test ---
def _unit_test():
    logs = pd.DataFrame({
        'cost': [10, 12, 8, 11],
        'timestamp': pd.date_range('2024-01-01', periods=4)
    })
    pnl = [0, 20, -10, 30, -5, 15]
    hedged = [0, 10, -5, 12, -2, 8]
    pnl_data = {'pnl': pnl, 'hedged_pnl': hedged}
    print('Hedging cost:', calculate_hedging_costs(logs))
    print('Effectiveness:', calculate_hedge_effectiveness(pnl, hedged))
    print('Report:\n', generate_performance_report(logs, pnl_data))

if __name__ == "__main__":
    _unit_test()
