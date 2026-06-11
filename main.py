import asyncio
import os
import threading
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot import router
import uvicorn
from webhook import app

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    print("Bot started!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

def start_webhook():
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Запускаем webhook сервер в отдельном потоке
    webhook_thread = threading.Thread(target=start_webhook, daemon=True)
    webhook_thread.start()
    # Запускаем бота
    asyncio.run(start_bot())