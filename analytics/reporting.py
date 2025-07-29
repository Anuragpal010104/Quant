import os
import csv
import sqlite3
import datetime
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

DB_PATH = "hedge_logs.db"
CSV_PATH = "hedge_logs.csv"

# --- Logging ---
def log_hedge_execution(details: dict):
    """
    Save hedge execution details to CSV and SQLite DB.
    """
    # CSV
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, mode='a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(details.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(details)
    # SQLite
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hedge_logs (
        asset TEXT, size REAL, price REAL, cost REAL, timestamp TEXT, strategy TEXT, status TEXT
    )''')
    c.execute('''INSERT INTO hedge_logs (asset, size, price, cost, timestamp, strategy, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (details['asset'], details['size'], details['price'], details['cost'], details['timestamp'], details['strategy'], details['status']))
    conn.commit()
    conn.close()

# --- Reporting ---
def generate_hedge_report(asset: str, timeframe: str = "7d") -> Dict:
    """
    Load hedge logs for asset and timeframe, compute stats.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=int(timeframe.rstrip('d')))).isoformat()
    c.execute('''SELECT size, cost, price, status, timestamp FROM hedge_logs WHERE asset=? AND timestamp>=?''', (asset, since))
    rows = c.fetchall()
    conn.close()
    total_hedges = len(rows)
    cum_volume = sum(abs(r[0]) for r in rows)
    avg_cost = sum(r[1] for r in rows) / total_hedges if total_hedges else 0
    avg_slippage = 0  # Placeholder, can be computed if slippage is logged
    effectiveness = 0  # Optional: needs price data
    return {
        'total_hedges': total_hedges,
        'cumulative_volume': cum_volume,
        'average_cost': avg_cost,
        'average_slippage': avg_slippage,
        'effectiveness': effectiveness,
        'rows': rows
    }

def generate_portfolio_risk_summary() -> Dict:
    """
    Aggregate historical risk exposures (delta, VaR) over time.
    """
    # Placeholder: would require risk logs
    return {}

def plot_risk_metrics_over_time(risk_history: List[Dict], metric: str = "delta", out_path: Optional[str] = None):
    """
    Plot risk metric over time and save as PNG.
    """
    times = [r['timestamp'] for r in risk_history]
    values = [r[metric] for r in risk_history]
    plt.figure(figsize=(10, 4))
    plt.plot(times, values, marker='o')
    plt.title(f"{metric.capitalize()} Over Time")
    plt.xlabel("Time")
    plt.ylabel(metric.capitalize())
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path)
    else:
        plt.show()
