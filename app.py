import os
import logging
import threading
import asyncio
from flask import Flask, jsonify
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN
from database import init_db
from handlers import (
    startgame_cmd, profile_cmd, leaderboard_cmd, history_cmd,
    daily_cmd, help_cmd, cancelgame_cmd, endgame_cmd, button_handler
)

# --- FLASK SETUP (For Render Health Check) ---
flask_app = Flask(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR) # Flask logs hide karo

@flask_app.route('/')
def index():
    return "Marvel vs DC Bot is online ⚔️"

@flask_app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_flask():
    """Flask ko background mein port pe bind karta hai"""
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


# --- TELEGRAM BOT SETUP ---
async def start_telegram_bot():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing!")
        return

    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("startgame", startgame_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancelgame", cancelgame_cmd))
    app.add_handler(CommandHandler("endgame", endgame_cmd))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logging.info("Starting Telegram Bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("✅ Telegram Bot is now actively listening!")
    
    # Bot ko zinda rakho
    while True:
        await asyncio.sleep(3600)

def run_bot_thread():
    """Bot ko alag event loop mein chalata hai"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_telegram_bot())


# --- MAIN EXECUTION ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 1. Flask ko background thread mein start karo (Render ko happy karega)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 2. Bot ko main thread mein start karo (Taaki process exit na ho)
    run_bot_thread()
