from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from config import TELEGRAM_BOT_TOKEN
from utils.logger import logger
import os
import asyncio
from exchange_api.deribit_api import DeribitClient
from risk_engine.risk_metrics import (
    calculate_delta, calculate_gamma, calculate_vega, calculate_theta,
    aggregate_portfolio_risks, calculate_var
)
import json
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hedge_commands import hedge_now, hedge_status, hedge_callback_handler
from ml.volatility_model import format_vol_forecast_message
from portfolio.multi_asset_hedging import (
    calculate_cross_asset_correlation, compute_portfolio_exposure, optimal_hedge_allocation, format_hedge_portfolio_message
)
from hedging.advanced_strategies import construct_iron_condor, construct_butterfly_spread, construct_straddle, evaluate_strategy_payoff
from backtesting.backtest_engine import BacktestEngine, delta_neutral_strategy
from compliance.reporting import generate_risk_report
from analytics.performance_attribution import generate_performance_report
import numpy as np
import pandas as pd

load_dotenv(dotenv_path=".env.local")
USE_MOCK = os.getenv("USE_MOCK_DERIBIT", "False").lower() == "true"

monitoring_tasks = {}

# Store user monitoring context (symbol, position_size, threshold)
user_monitor_context = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I am your trading risk management bot.')

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        client = DeribitClient()
        await client.authenticate()
        await client.close()
        await update.message.reply_text("✅ Bot is online and Deribit API reachable!")
    except Exception as e:
        await update.message.reply_text(f"❌ Deribit API error: {e}")

async def risk_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Calculating risk summary, please wait...")
    try:
        client = DeribitClient()
        await client.authenticate()
        # Load positions (mocked or from file)
        MOCK_POSITIONS_PATH = "mock_positions.json"
        if os.path.exists(MOCK_POSITIONS_PATH):
            with open(MOCK_POSITIONS_PATH, "r") as f:
                positions = json.load(f)
        else:
            positions = [
                {"instrument_name": "BTC-30AUG24-60000-C", "size": 1, "type": "option", "option_type": "call", "S": 57000, "K": 60000, "T": 0.1, "r": 0.05, "sigma": 0.65},
                {"instrument_name": "BTC-PERPETUAL", "size": 0.5, "type": "spot", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}
            ]
        # Compute Greeks
        for pos in positions:
            if pos["type"] == "option":
                pos["delta"] = calculate_delta(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"], pos["option_type"])
                pos["gamma"] = calculate_gamma(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"])
                pos["vega"] = calculate_vega(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"])
                pos["theta"] = calculate_theta(pos["S"], pos["K"], pos["T"], pos["r"], pos["sigma"], pos["option_type"])
            else:
                pos["delta"] = pos["size"]
                pos["gamma"] = 0
                pos["vega"] = 0
                pos["theta"] = 0
        agg = aggregate_portfolio_risks(positions)
        price_series = [57000 + 1000 * __import__('math').sin(i/5) for i in range(100)]
        var = calculate_var(price_series)
        summary = (
            f"\U0001F4CA <b>Portfolio Risk Summary</b>\n"
            f"Delta: <b>{agg['delta']:.4f}</b>\n"
            f"Gamma: <b>{agg['gamma']:.4f}</b>\n"
            f"Vega: <b>{agg['vega']:.4f}</b>\n"
            f"Theta: <b>{agg['theta']:.4f}</b>\n"
            f"VaR (mock): <b>{var:.2f}</b>\n"
        )
        await client.close()
        await update.message.reply_text(summary, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data.lower()
    ctx = user_monitor_context.get(chat_id, {})
    if data == "hedge_now":
        # Mocked hedge logic
        symbol = ctx.get("symbol", "BTC")
        size = ctx.get("position_size", 0.0)
        threshold = ctx.get("risk_threshold", 0.0)
        # Compute optimal hedge size (mocked)
        hedge_size = size - threshold
        # Mock execution
        status = "success"
        cost = abs(hedge_size) * 57000  # Mock price
        slippage = 0.001 * cost
        msg = (
            f"✅ Hedge Executed\n"
            f"Asset: {symbol}\n"
            f"Hedge Size: {hedge_size:.4f}\n"
            f"Instrument: {symbol}-PERPETUAL\n"
            f"Estimated Cost: ${cost:.2f}\n"
            f"Estimated Slippage: ${slippage:.2f}\n"
            f"Status: {status}"
        )
        await query.edit_message_text(msg)
    elif data == "adjust_threshold":
        await query.edit_message_text("Please send the new risk threshold (as a number):")
        # Set a flag to expect next message as threshold
        ctx["awaiting_threshold"] = True
        user_monitor_context[chat_id] = ctx
    elif data == "stop_monitoring":
        monitoring_tasks[chat_id] = False
        await query.edit_message_text("🛑 Stopped risk monitoring.")
    else:
        await query.edit_message_text("Unknown action.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ctx = user_monitor_context.get(chat_id, {})
    if ctx.get("awaiting_threshold"):
        try:
            new_threshold = float(update.message.text)
            ctx["risk_threshold"] = new_threshold
            ctx["awaiting_threshold"] = False
            user_monitor_context[chat_id] = ctx
            await update.message.reply_text(f"Risk threshold updated to {new_threshold}.")
        except Exception:
            await update.message.reply_text("Invalid threshold. Please send a number.")

# Update monitor_risk to store context
async def monitor_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Usage: /monitor_risk <symbol> <position_size> <risk_threshold>")
            return
        symbol = args[0].upper()
        position_size = float(args[1])
        risk_threshold = float(args[2])
        chat_id = update.effective_chat.id
        user_monitor_context[chat_id] = {"symbol": symbol, "position_size": position_size, "risk_threshold": risk_threshold}
        await update.message.reply_text(f"Started monitoring {symbol} with position size {position_size} and risk threshold {risk_threshold}.")

        async def monitor_loop():
            import time
            while monitoring_tasks.get(chat_id):
                try:
                    client = DeribitClient()
                    await client.authenticate()
                    # For demo, use only Deribit. Extend to OKX/Bybit as needed.
                    positions = [
                        {"instrument_name": f"{symbol}-PERPETUAL", "size": position_size, "type": "spot", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}
                    ]
                    for pos in positions:
                        pos["delta"] = pos["size"]
                        pos["gamma"] = 0
                        pos["vega"] = 0
                        pos["theta"] = 0
                    agg = aggregate_portfolio_risks(positions)
                    price_series = [57000 + 1000 * __import__('math').sin(i/5) for i in range(100)]
                    var = calculate_var(price_series)
                    breached = agg['delta'] > user_monitor_context[chat_id]["risk_threshold"]
                    if breached:
                        keyboard = [
                            [InlineKeyboardButton("Hedge Now", callback_data="hedge_now")],
                            [InlineKeyboardButton("Adjust Threshold", callback_data="adjust_threshold")],
                            [InlineKeyboardButton("Stop Monitoring", callback_data="stop_monitoring")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        msg = (
                            f"⚠️ <b>Risk Alert for {symbol}</b>\n"
                            f"Delta: <b>{agg['delta']:.4f}</b>\n"
                            f"VaR: <b>{var:.2f}</b>\n"
                            f"Suggested hedge: SELL {agg['delta'] - user_monitor_context[chat_id]['risk_threshold']:.4f} {symbol} futures\n"
                            f"Estimated cost: ~${abs(agg['delta'] - user_monitor_context[chat_id]['risk_threshold']) * 57000:.2f}"
                        )
                        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=reply_markup)
                    await client.close()
                except Exception as e:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Monitor error: {e}")
                await asyncio.sleep(30)  # Monitor interval
        # Start background task
        monitoring_tasks[chat_id] = True
        asyncio.create_task(monitor_loop())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def stop_risk_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if monitoring_tasks.get(chat_id):
        monitoring_tasks[chat_id] = False
        await update.message.reply_text("🛑 Stopped risk monitoring.")
    else:
        await update.message.reply_text("No active risk monitoring task found.")

# --- ML Volatility Forecasting Command ---
async def vol_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asset = context.args[0] if context.args else "BTC"
    # Mock: Generate random forecast
    forecast = np.random.uniform(0.3, 0.8)
    action = "Hedge" if forecast > 0.5 else "Hold"
    msg = format_vol_forecast_message(asset, forecast, "RandomForest", action)
    await update.message.reply_text(msg)

# --- Multi-Asset Portfolio Hedging Command ---
async def hedge_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mock positions and prices
    positions = [
        {'symbol': 'BTC', 'delta': 1.2, 'gamma': 0.1, 'vega': 0.2, 'theta': -0.01},
        {'symbol': 'ETH', 'delta': -0.5, 'gamma': 0.05, 'vega': 0.1, 'theta': -0.005},
        {'symbol': 'BTC', 'delta': -0.7, 'gamma': 0.02, 'vega': 0.05, 'theta': -0.002}
    ]
    price_data = {'BTC': [10000, 10100, 10200, 10150, 10300], 'ETH': [200, 202, 204, 203, 207]}
    exposures = compute_portfolio_exposure(positions)
    corr = calculate_cross_asset_correlation(price_data)
    alloc = optimal_hedge_allocation(exposures, corr)
    msg = format_hedge_portfolio_message(alloc)
    await update.message.reply_text(msg)

# --- Advanced Options Strategies Command ---
async def strategy_payoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] not in ["iron_condor", "butterfly", "straddle"]:
        await update.message.reply_text("Usage: /strategy_payoff <iron_condor|butterfly|straddle>")
        return
    S, K, width, T, r, sigma = 100, 100, 10, 0.1, 0.01, 0.5
    price_range = np.linspace(80, 120, 41)
    if args[0] == "iron_condor":
        strat = construct_iron_condor(S, K, width, T, r, sigma)
    elif args[0] == "butterfly":
        strat = construct_butterfly_spread(S, K, width, T, r, sigma)
    else:
        strat = construct_straddle(S, K, T, r, sigma)
    payoff = evaluate_strategy_payoff(strat, price_range)
    msg = f"Strategy: {args[0].replace('_', ' ').title()}\nPayoff (sample): {payoff[:5]}..."
    await update.message.reply_text(msg)

# --- Backtesting Command ---
async def backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    engine = BacktestEngine()
    price_data = pd.DataFrame({'close': np.linspace(10000, 11000, 100)})
    positions = []
    res = engine.run_backtest(delta_neutral_strategy, positions, price_data, 'delta_neutral')
    msg = f"Backtest complete. Final PnL: {res.get('final_pnl', 0):.2f}"
    await update.message.reply_text(msg)

# --- Regulatory Compliance Command ---
async def risk_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    positions = [
        {"instrument_name": "BTC-30AUG24-60000-C", "size": 1, "type": "option", "option_type": "call", "S": 57000, "K": 60000, "T": 0.1, "r": 0.05, "sigma": 0.65},
        {"instrument_name": "BTC-PERPETUAL", "size": 0.5, "type": "spot", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}
    ]
    metrics = aggregate_portfolio_risks(positions)
    compliance_thresholds = {'delta': 1.0, 'var': 1000}
    report = generate_risk_report(positions, metrics, compliance_thresholds)
    await update.message.reply_text(report, parse_mode='HTML')

# --- Performance Attribution Command ---
async def performance_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mock hedge logs and pnl data
    hedge_logs = pd.DataFrame({'cost': [10, 12, 8, 11]})
    pnl_data = {'pnl': [100, 120, 110, 130], 'hedged_pnl': [90, 115, 108, 125]}
    report = generate_performance_report(hedge_logs, pnl_data)
    await update.message.reply_text(report, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Use /monitor_risk, /stop_risk_monitoring, /risk_summary, /health, /vol_forecast, /hedge_portfolio, /strategy_payoff, /backtest, /risk_report, /performance_report"
    )
    await update.message.reply_text(msg)

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Not implemented yet.")

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Not implemented yet.")

async def set_thresholds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Not implemented yet.")

# --- ASYNC VERSIONS for hedge_now and hedge_status ---
from execution.execution_engine import ExecutionEngine
engine = ExecutionEngine()

async def hedge_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /hedge_now <asset> <size> <side>")
        return
    asset, size, side = args[0], float(args[1]), args[2]
    await update.message.reply_text(f"\U0001F4CD Executing Hedge: {asset} | Size: {size} | Side: {side.title()}...")
    # Simulate execution (replace with real logic as needed)
    result = engine.execute_perpetual_hedge(asset, size, side)
    price = result.get('price', 0)
    slippage = result.get('slippage', 0)
    cost = result.get('cost', 0)
    msg = (f"\u2705 Executed at ${price:,.2f} | Slippage: {slippage/price*100 if price else 0:.2f}% | Cost: ${cost:.2f}")
    await update.message.reply_text(msg)

async def hedge_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /hedge_status <asset>")
        return
    asset = args[0].upper()
    # Simulate lookup (replace with real logic as needed)
    last = {'timestamp': '2025-07-11T16:00:00Z', 'size': 1, 'side': 'sell', 'price': 57000, 'cost': 100, 'slippage': 0.5}
    msg = (f"Last Hedge for {asset}:\n"
           f"Time: {last['timestamp']}\n"
           f"Size: {last['size']} | Side: {last['side']}\n"
           f"Price: ${last['price']:,.2f} | Cost: ${last['cost']:.2f}\n"
           f"Slippage: {last['slippage']:.4f}")
    await update.message.reply_text(msg)

def main():
    logger.info("Starting Telegram bot...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health))
    application.add_handler(CommandHandler("risk_summary", risk_summary))
    application.add_handler(CommandHandler("monitor_risk", monitor_risk))
    application.add_handler(CommandHandler("stop_risk_monitoring", stop_risk_monitoring))
    application.add_handler(CommandHandler("hedge_now", hedge_now))
    application.add_handler(CommandHandler("hedge_status", hedge_status))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CallbackQueryHandler(hedge_callback_handler))
    application.add_handler(CommandHandler("positions", positions_command))
    application.add_handler(CommandHandler("orders", orders_command))
    application.add_handler(CommandHandler("set_thresholds", set_thresholds_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("vol_forecast", vol_forecast))
    application.add_handler(CommandHandler("hedge_portfolio", hedge_portfolio))
    application.add_handler(CommandHandler("strategy_payoff", strategy_payoff))
    application.add_handler(CommandHandler("backtest", backtest))
    application.add_handler(CommandHandler("risk_report", risk_report))
    application.add_handler(CommandHandler("performance_report", performance_report))
    application.run_polling()

if __name__ == '__main__':
    main()
