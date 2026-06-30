import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Добавляем корень проекта в пути поиска
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import engine, Base
from backend.api import router as api_router
from bot.main import seed_db  # Импортируем функцию для создания тестовых данных
from telegram.ext import Application
from bot.handlers import get_main_handlers
from bot.scheduler import setup_scheduler

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Глобальная переменная для приложения бота
bot_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Этап запуска (Startup)
    print("Инициализация базы данных...")
    Base.metadata.create_all(bind=engine)
    seed_db()
    
    if TOKEN and TOKEN != "твой_токен_здесь":
        print("Запуск Telegram-бота...")
        global bot_app
        bot_app = Application.builder().token(TOKEN).build()
        
        for handler in get_main_handlers():
            bot_app.add_handler(handler)
            
        setup_scheduler(bot_app)
        
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        print("Telegram-бот успешно запущен в фоне!")
    else:
        print("ВНИМАНИЕ: BOT_TOKEN не установлен, бот не запущен.")
        
    yield
    
    # Этап выключения (Shutdown)
    if bot_app:
        print("Остановка Telegram-бота...")
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

# Создание FastAPI приложения
app = FastAPI(lifespan=lifespan)

# Настройка CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутера
app.include_router(api_router)

# Раздача статических файлов Mini App
app.mount("/", StaticFiles(directory="miniapp", html=True), name="miniapp")

# При локальном запуске (для тестирования)
if __name__ == "__main__":
    import uvicorn
    # Используем порт 8000 локально, либо порт из переменной окружения (для Railway)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
