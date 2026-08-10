import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers import (
    startgame_cmd, profile_cmd, leaderboard_cmd, history_cmd,
    daily_cmd, help_cmd, cancelgame_cmd, endgame_cmd, button_handler
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def start_bot_loop():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
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
    
    logger.info("Starting Telegram bot polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running indefinitely
    while True:
        import asyncio
        await asyncio.sleep(3600)
