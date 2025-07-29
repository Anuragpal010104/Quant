import os
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from utils.logger import logger
from exchange_api.deribit_api import DeribitClient
from risk_engine.risk_metrics import (
    calculate_delta, calculate_gamma, calculate_vega, calculate_theta,
    aggregate_portfolio_risks, calculate_var
)
from hedging_engine import HedgingEngine
import json
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USE_MOCK = os.getenv("USE_MOCK_DERIBIT", "False").lower() == "true"

monitoring_tasks = {}
user_monitor_context = {}

# --- Command Handlers ---
def monitor_risk(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 3:
        update.message.reply_text("Usage: /monitor_risk <asset> <position_size> <delta_threshold>")
        return
    asset = args[0].upper()
    position_size = float(args[1])
    delta_threshold = float(args[2])
    chat_id = update.effective_chat.id
    user_monitor_context[chat_id] = {"asset": asset, "position_size": position_size, "delta_threshold": delta_threshold}
    update.message.reply_text(f"Started monitoring {asset} with position size {position_size} and delta threshold {delta_threshold}.")
    def monitor_loop():
        while monitoring_tasks.get(chat_id):
            try:
                client = DeribitClient()
                client.authenticate()
                positions = [{"instrument_name": f"{asset}-PERPETUAL", "size": position_size, "type": "spot", "option_type": None, "S": 57000, "K": 0, "T": 0, "r": 0, "sigma": 0}]
                for pos in positions:
                    pos["delta"] = pos["size"]
                agg = aggregate_portfolio_risks(positions)
                breached = agg['delta'] > delta_threshold
                if breached:
                    keyboard = [
                        [InlineKeyboardButton("Hedge Now", callback_data=f"hedge_now|{asset}|{agg['delta']}")],
                        [InlineKeyboardButton("View Analytics", callback_data="view_analytics")],
                        [InlineKeyboardButton("Adjust Threshold", callback_data="adjust_threshold")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    msg = (
                        f"⚠️ Risk Threshold Breached: Delta = {agg['delta']:.2f} > {delta_threshold}. "
                        f"Recommended Hedge: {-agg['delta'] + delta_threshold:.2f} {asset}"
                    )
                    context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=reply_markup)
                time.sleep(30)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)
    monitoring_tasks[chat_id] = True
    threading.Thread(target=monitor_loop, daemon=True).start()

def hedge_now(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Usage: /hedge_now <asset> <size>")
        return
    asset = args[0].upper()
    size = float(args[1])
    engine = HedgingEngine(logger=logger)
    # Mock market data
    market_data = {"option_delta": 1}
    hedge_size = engine.compute_optimal_hedge_size({"delta": size}, market_data, strategy="perpetual")
    order = engine.execute_hedge("perpetual", asset, hedge_size, notify=lambda msg: update.message.reply_text(msg))
    update.message.reply_text(f"Hedge order sent: {order}")

def hedge_status(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 1:
        update.message.reply_text("Usage: /hedge_status <asset>")
        return
    asset = args[0].upper()
    # Mock: show current exposure
    update.message.reply_text(f"Current exposure for {asset}: 0.0 (mock)")

def auto_hedge(update: Update, context: CallbackContext):
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Usage: /auto_hedge <strategy> <threshold>")
        return
    strategy = args[0]
    threshold = float(args[1])
    update.message.reply_text(f"Auto-hedging enabled: {strategy} with threshold {threshold}")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    chat_id = query.message.chat_id
    if data.startswith("hedge_now"):
        _, asset, delta = data.split("|")
        engine = HedgingEngine(logger=logger)
        market_data = {"option_delta": 1}
        hedge_size = engine.compute_optimal_hedge_size({"delta": float(delta)}, market_data, strategy="perpetual")
        order = engine.execute_hedge("perpetual", asset, hedge_size, notify=lambda msg: query.edit_message_text(msg))
        query.edit_message_text(f"Hedge order sent: {order}")
    elif data == "view_analytics":
        query.edit_message_text("Portfolio Greeks and VaR: (mock)")
    elif data == "adjust_threshold":
        query.edit_message_text("Send new delta threshold:")
        user_monitor_context[chat_id]["awaiting_threshold"] = True
    else:
        query.edit_message_text("Unknown action.")

def handle_text(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    ctx = user_monitor_context.get(chat_id, {})
    if ctx.get("awaiting_threshold"):
        try:
            new_threshold = float(update.message.text)
            ctx["delta_threshold"] = new_threshold
            ctx["awaiting_threshold"] = False
            user_monitor_context[chat_id] = ctx
            update.message.reply_text(f"Delta threshold updated to {new_threshold}.")
        except Exception:
            update.message.reply_text("Invalid threshold. Please send a number.")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("monitor_risk", monitor_risk))
    dp.add_handler(CommandHandler("hedge_now", hedge_now))
    dp.add_handler(CommandHandler("hedge_status", hedge_status))
    dp.add_handler(CommandHandler("auto_hedge", auto_hedge))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Use /monitor_risk, /hedge_now, /hedge_status, /auto_hedge")))
    dp.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Welcome to the Risk Bot!")))
    dp.add_handler(CommandHandler("stop", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("set_thresholds", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("positions", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("orders", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("risk_report", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("hedge_history", lambda u, c: u.message.reply_text("Not implemented yet.")))
    dp.add_handler(CommandHandler("hedge_status", hedge_status))
    dp.add_handler(CommandHandler("auto_hedge", auto_hedge))
    dp.add_handler(CommandHandler("monitor_risk", monitor_risk))
    dp.add_handler(CommandHandler("hedge_now", hedge_now))
    dp.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Use /monitor_risk, /hedge_now, /hedge_status, /auto_hedge")))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
