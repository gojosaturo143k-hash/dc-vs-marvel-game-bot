import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "Marvel vs DC Bot is online ⚔️"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
