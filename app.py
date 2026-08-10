import os
import threading
import logging
from flask import Flask, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    return "Marvel vs DC Bot is online ⚔️"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_bot():
    import asyncio
    from bot import start_bot_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot_loop())

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
else:
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
