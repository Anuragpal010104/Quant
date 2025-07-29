from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from execution.execution_engine import ExecutionEngine
from analytics.reporting import get_last_hedge_execution

engine = ExecutionEngine()

# /hedge_now <asset> <size> <side>
def hedge_now(update: Update, context: CallbackContext):
    args = context.args
    if len(args) != 3:
        update.message.reply_text("Usage: /hedge_now <asset> <size> <side>")
        return
    asset, size, side = args[0].upper(), float(args[1]), args[2].lower()
    update.message.reply_text(f"\U0001F4CD Executing Hedge: {asset} | Size: {size} | Side: {side.title()}...")
    result = engine.execute_perpetual_hedge(asset, size, side)
    price = result['price']
    slippage = result['slippage']
    cost = result['cost']
    msg = (f"\u2705 Executed at ${price:,.2f} | Slippage: {slippage/price*100:.2f}% | Cost: ${cost:.2f}")
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
    if query.data == 'hedge_now':
        query.answer()
        query.edit_message_text("Manual hedge triggered! (Implement logic as needed)")
    elif query.data == 'adjust_threshold':
        query.answer()
        query.edit_message_text("Threshold adjustment coming soon.")
    elif query.data == 'view_analytics':
        query.answer()
        query.edit_message_text("Analytics view coming soon.")
