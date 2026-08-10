import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "game.db")
LOBBY_TIMEOUT_SECONDS = 900
MIN_PLAYERS = 2
MAX_PLAYERS = 10
