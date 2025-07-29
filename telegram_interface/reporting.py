import os
import io
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from analytics.reporting import generate_hedge_report, plot_risk_metrics_over_time
from risk_engine.risk_metrics import aggregate_portfolio_risks, calculate_var
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
USE_HEADLESS = os.getenv("USE_HEADLESS", "False").lower() == "true"

# --- /hedge_status <asset> ---
def hedge_status(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 1:
        update.message.reply_text("Usage: /hedge_status <asset>")
        return
    asset = args[0].upper()
    # Mocked: Replace with real position/hedge lookup
    net_delta = 0.4
    hedge = -0.8
    hedge_ex = "Perpetual OKX"
    var = 2340
    msg = (f"\U0001F4CA {asset} Exposure: 1.2 {asset} | Hedge: {hedge:+.2f} ({hedge_ex}) | "
           f"Net Delta: {net_delta:.2f} | VaR: ${var:,.0f}")
    update.message.reply_text(msg)

# --- /hedge_history <asset> <days> ---
def hedge_history(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Usage: /hedge_history <asset> <days>")
        return
    asset = args[0].upper()
    days = args[1]
    report = generate_hedge_report(asset, timeframe=f"{days}d")
    msg = (f"Hedged {report['total_hedges']} times in last {days}d | "
           f"Avg Slippage: {report['average_slippage']}bps | Total Cost: ${report['average_cost']*report['total_hedges']:.2f}")
    update.message.reply_text(msg)

# --- /risk_report ---
def risk_report(update: Update, context: CallbackContext):
    # Mocked: Replace with real portfolio data
    agg = {'delta': 0.12, 'gamma': 0.01, 'vega': 0.05, 'theta': -0.02}
    var = 1920
    msg = (f"\U0001F4C9 Portfolio Risk Report\n"
           f"Delta: {agg['delta']:.2f}\nGamma: {agg['gamma']:.2f}\nVega: {agg['vega']:.2f}\nTheta: {agg['theta']:.2f}\nVaR: ${var:,.0f}")
    update.message.reply_text(msg)

# --- Real-Time Alerts ---
def send_hedge_executed_alert(context: CallbackContext, details: dict, chat_id: int):
    msg = (f"\u2705 Hedge Executed: {details['size']:+.4f} {details['asset']} @ {details['exchange']}, ${details['price']:,} | "
           f"Slippage: {details['slippage_bps']:.1f}bps | Cost: ${details['cost_usd']:.2f}")
    context.bot.send_message(chat_id=chat_id, text=msg)

def send_threshold_breach_alert(context: CallbackContext, asset: str, net_delta: float, threshold: float, chat_id: int):
    msg = (f"\u26A0\uFE0F Delta Exposure Breach: {asset} Net Delta = {net_delta:.2f} > Threshold ({threshold}). Recommend hedge {-net_delta + threshold:.2f} {asset}")
    keyboard = [[InlineKeyboardButton("Hedge Now", callback_data=f"hedge_now|{asset}|{net_delta}"),
                 InlineKeyboardButton("View Analytics", callback_data="view_analytics"),
                 InlineKeyboardButton("Stop Auto Hedge", callback_data="stop_auto_hedge")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup)

# --- Analytics Charts ---
def send_risk_chart(update: Update, context: CallbackContext, risk_history, metric: str = "delta"):
    if USE_HEADLESS:
        plt.switch_backend('Agg')
    buf = io.BytesIO()
    plot_risk_metrics_over_time(risk_history, metric, out_path=buf)
    buf.seek(0)
    update.message.reply_photo(photo=buf, caption=f"{metric.capitalize()} Over Time")
    buf.close()

# --- Scheduled Reporting ---
def scheduled_portfolio_summary(context: CallbackContext):
    # Mocked: Replace with real data
    msg = ("\U0001F4C8 Portfolio Summary: Total Delta: 0.12 | VaR: $1,920 | PnL: +$140 (last 6h)")
    for chat_id in context.job.context:
        context.bot.send_message(chat_id=chat_id, text=msg)

# --- Command Registration Helper ---
def register_reporting_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("hedge_status", hedge_status))
    dispatcher.add_handler(CommandHandler("hedge_history", hedge_history))
    dispatcher.add_handler(CommandHandler("risk_report", risk_report))
    # Add more as needed
