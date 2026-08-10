import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers import (
    startgame_cmd, profile_cmd, leaderboard_cmd, history_cmd,
    daily_cmd, help_cmd, cancelgame_cmd, endgame_cmd, button_handler
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s)

def main():
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
    app.add_handler(CommandHandler("startgame", startgame_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancelgame", cancelgame_cmd))
    app.add_handler(CommandHandler("endgame", endgame_cmd))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logging.info("Starting Telegram Bot...")
    app.run_polling()

if __name__ == '__main__':
    main()
