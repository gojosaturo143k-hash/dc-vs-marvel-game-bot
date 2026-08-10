import os
import asyncio
import logging
from flask import Flask, jsonify
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return "Marvel vs DC Bot is online ⚔️"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

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
    
    # Bot ko zinda rakho
    while True:
        await asyncio.sleep(3600)

def create_app():
    # Uvicorn ye function call karega
    asyncio.create_task(start_telegram_bot())
    return WsgiToAsgi(app)

if __name__ == '__main__':
    # Sirf local testing ke liye
    async def main():
        task = asyncio.create_task(start_telegram_bot())
        import uvicorn
        config = uvicorn.Config(app="app:create_app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), factory=True, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
        
    asyncio.run(main())
