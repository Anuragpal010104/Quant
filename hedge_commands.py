from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from execution.execution_engine import ExecutionEngine

engine = ExecutionEngine()

# /hedge_now <asset> <size> <side>
def hedge_now(update: Update, context: CallbackContext):
    args = context.args
    if len(args) != 3:
        update.message.reply_text("Usage: /hedge_now <asset> <size> <side>")
        return
    asset, size, side = args[0], float(args[1]), args[2]
    update.message.reply_text(f"\U0001F4CD Executing Hedge: {asset} | Size: {size} | Side: {side.title()}...")
    result = engine.execute_perpetual_hedge(asset, size, side)
    price = result.get('price', 0)
    slippage = result.get('slippage', 0)
    cost = result.get('cost', 0)
    msg = (f"\u2705 Executed at ${price:,.2f} | Slippage: {slippage/price*100 if price else 0:.2f}% | Cost: ${cost:.2f}")
    update.message.reply_text(msg)

# /hedge_status <asset>
def hedge_status(update: Update, context: CallbackContext):
    args = context.args
    if len(args) != 1:
        update.message.reply_text("Usage: /hedge_status <asset>")
        return
    asset = args[0].upper()
    last = get_last_hedge_execution(asset)
    if not last:
        update.message.reply_text(f"No hedge found for {asset}.")
        return
    msg = (f"Last Hedge for {asset}:\n"
           f"Time: {last['timestamp']}\n"
           f"Size: {last['size']} | Side: {last['side']}\n"
           f"Price: ${last['price']:,.2f} | Cost: ${last['cost']:.2f}\n"
           f"Slippage: {last['slippage']:.4f}")
    update.message.reply_text(msg)

# Inline button interaction for risk alerts
def send_risk_alert_with_buttons(chat_id, bot, alert_msg):
    keyboard = [
        [InlineKeyboardButton("Hedge Now", callback_data='hedge_now')],
        [InlineKeyboardButton("Adjust Threshold", callback_data='adjust_threshold')],
        [InlineKeyboardButton("View Analytics", callback_data='view_analytics')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=chat_id, text=alert_msg, reply_markup=reply_markup)

# Callback query handler for inline buttons
def hedge_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()
    query.edit_message_text(f"Button pressed: {data}")

def get_last_hedge_execution(asset):
    import csv
    try:
        with open('hedge_logs.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            hedges = [row for row in reader if row.get('asset', '').upper() == asset.upper()]
            if hedges:
                return hedges[-1]
    except Exception:
        pass
    return None
