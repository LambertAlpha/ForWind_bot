#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
import schedule
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
import ccxt

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
AUTHORIZED_USER_IDS = [int(id) for id in os.getenv('AUTHORIZED_USER_IDS', '').split(',') if id]

# Global variables
is_monitoring = False
monitor_thread = None
trading_pairs = []
price_history = {}  # Structure: {symbol: [{timestamp: float, price: float}, ...]}

# Data storage functions
def save_trading_pairs():
    with open('trading_pairs.json', 'w') as f:
        json.dump(trading_pairs, f)

def load_trading_pairs():
    global trading_pairs
    try:
        if os.path.exists('trading_pairs.json'):
            with open('trading_pairs.json', 'r') as f:
                trading_pairs = json.load(f)
    except Exception as e:
        logger.error(f"Error loading trading pairs: {e}")
        trading_pairs = []

# Initialize exchange
def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
    })

# Price monitoring functions
def get_current_price(symbol):
    try:
        exchange = get_exchange()
        ticker = exchange.fetch_ticker(f"{symbol}/USDT")
        return ticker['last']
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return None

def check_price_increase(symbol):
    global price_history
    
    current_price = get_current_price(symbol)
    if current_price is None:
        return False, 0
    
    now = time.time()
    
    # Add current price to history
    if symbol not in price_history:
        price_history[symbol] = []
    
    price_history[symbol].append({
        'timestamp': now,
        'price': current_price
    })
    
    # Remove old prices (older than 5 minutes)
    five_min_ago = now - 300  # 5 minutes in seconds
    price_history[symbol] = [p for p in price_history[symbol] if p['timestamp'] > five_min_ago]
    
    # Check if we have enough history
    if len(price_history[symbol]) < 2:
        return False, 0
    
    # Find the oldest price in the 5 min window
    oldest_price = min(price_history[symbol], key=lambda x: x['timestamp'])
    
    # Calculate percentage increase
    percent_increase = ((current_price - oldest_price['price']) / oldest_price['price']) * 100
    
    return percent_increase >= 2.0, percent_increase

def monitor_prices(context: CallbackContext):
    global trading_pairs, is_monitoring
    
    while is_monitoring:
        for symbol in trading_pairs:
            try:
                increased, percent = check_price_increase(symbol)
                if increased:
                    message = f"🚀 *PRICE ALERT* 🚀\n{symbol}/USDT has increased by {percent:.2f}% in the last 5 minutes!\nCurrent price: ${get_current_price(symbol)}"
                    for user_id in AUTHORIZED_USER_IDS:
                        context.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    logger.info(f"Alert sent for {symbol} - {percent:.2f}% increase")
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
        
        # Sleep for 5 seconds before checking again
        time.sleep(5)

# Command handlers
def check_auth(update: Update):
    """Check if user is authorized to use this bot"""
    user_id = update.effective_user.id
    if not AUTHORIZED_USER_IDS or user_id not in AUTHORIZED_USER_IDS:
        update.message.reply_text("⛔ You are not authorized to use this bot.")
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        return False
    return True

def start_command(update: Update, context: CallbackContext):
    """Start the monitoring process"""
    if not check_auth(update):
        return
    
    global is_monitoring, monitor_thread
    
    if is_monitoring:
        update.message.reply_text("Monitoring is already active! 👀")
        return
    
    if not trading_pairs:
        update.message.reply_text("Please add trading pairs first using /add command")
        return
    
    is_monitoring = True
    monitor_thread = threading.Thread(target=monitor_prices, args=(context,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    update.message.reply_text("✅ Monitoring started! I'll alert you when prices increase by 2%+ in 5 minutes.")
    logger.info(f"Monitoring started by user {update.effective_user.id}")

def end_command(update: Update, context: CallbackContext):
    """Stop the monitoring process"""
    if not check_auth(update):
        return
    
    global is_monitoring
    
    if not is_monitoring:
        update.message.reply_text("Monitoring is already stopped! 😴")
        return
    
    is_monitoring = False
    update.message.reply_text("❌ Monitoring stopped!")
    logger.info(f"Monitoring stopped by user {update.effective_user.id}")

def list_command(update: Update, context: CallbackContext):
    """List all trading pairs being monitored"""
    if not check_auth(update):
        return
    
    if not trading_pairs:
        update.message.reply_text("No trading pairs are being monitored.")
        return
    
    pairs_text = " ".join(trading_pairs)
    update.message.reply_text(f"📋 Monitored trading pairs: {pairs_text}")

def add_command(update: Update, context: CallbackContext):
    """Add a trading pair to monitor"""
    if not check_auth(update):
        return
    
    if not context.args:
        update.message.reply_text("Please provide a trading pair symbol. Example: /add BTC")
        return
    
    symbol = context.args[0].upper()
    
    # Check if symbol already exists
    if symbol in trading_pairs:
        update.message.reply_text(f"{symbol} is already being monitored.")
        return
    
    # Verify symbol exists
    try:
        price = get_current_price(symbol)
        if price is None:
            update.message.reply_text(f"❌ Could not find trading pair {symbol}/USDT")
            return
        
        trading_pairs.append(symbol)
        save_trading_pairs()
        
        update.message.reply_text(f"✅ Added {symbol}/USDT for monitoring.\nCurrent price: ${price}")
        logger.info(f"Added {symbol} by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error adding {symbol}: {e}")
        update.message.reply_text(f"❌ Error adding {symbol}/USDT: {str(e)}")

def delete_command(update: Update, context: CallbackContext):
    """Remove a trading pair from monitoring"""
    if not check_auth(update):
        return
    
    if not context.args:
        update.message.reply_text("Please provide a trading pair symbol. Example: /delete BTC")
        return
    
    symbol = context.args[0].upper()
    
    if symbol not in trading_pairs:
        update.message.reply_text(f"{symbol} is not being monitored.")
        return
    
    trading_pairs.remove(symbol)
    save_trading_pairs()
    
    update.message.reply_text(f"✅ Removed {symbol}/USDT from monitoring.")
    logger.info(f"Deleted {symbol} by user {update.effective_user.id}")

def help_command(update: Update, context: CallbackContext):
    """Display help information"""
    help_text = """
📊 *ForWind Bot Commands* 📊

/start - Start monitoring price changes
/end - Stop monitoring price changes
/list - List all trading pairs being monitored
/add SYMBOL - Add a trading pair (e.g. /add BTC)
/delete SYMBOL - Remove a trading pair (e.g. /delete BTC)
/help - Show this help message

The bot monitors for 2%+ price increases in 5 minute windows.
    """
    update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Start the bot"""
    # Load existing trading pairs
    load_trading_pairs()
    
    # Create the Updater
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("end", end_command))
    dispatcher.add_handler(CommandHandler("list", list_command))
    dispatcher.add_handler(CommandHandler("add", add_command))
    dispatcher.add_handler(CommandHandler("delete", delete_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Start the Bot
    updater.start_polling()
    logger.info("Bot started!")
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
