import os
import logging
from flask import Flask, jsonify
import asyncio
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return "Marvel vs DC Bot is online ⚔️"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_telegram_bot())
    except Exception as e:
        logging.error(f"Bot thread error: {e}")
    finally:
        loop.close()

async def start_telegram_bot():
    from config import BOT_TOKEN
    from database import init_db
    from bot import setup_bot_handlers
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is missing!")
        return

    init_db()
    application = setup_bot_handlers()
    
    logging.info("Initializing Telegram Bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logging.info("✅ Telegram Bot is now actively listening!")
    
    while True:
        await asyncio.sleep(3600)

# Render pe Gunicorn jab ye file load karega, ye line automatically bot start karegi
threading.Thread(target=run_bot_in_thread, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
