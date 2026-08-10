import os
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

# Ye function bot.py se call hoga jab Gunicorn start hoga
def run_bot_sync():
    import asyncio
    from bot import init_and_run_bot
    # Yahan hum naya event loop nahi banate, balki current Gunicorn loop use karte hain
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Bot ko background mein start karo bina main thread block kiye
    loop.create_task(init_and_run_bot())
    
    # Loop ko zinda rakho
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == '__main__':
    import threading
    bot_thread = threading.Thread(target=run_bot_sync, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
