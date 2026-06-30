import os
import sys

# Добавляем корневую папку проекта в sys.path, чтобы Python видел модули bot и database
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from telegram.ext import Application
from bot.handlers import get_main_handlers
from bot.scheduler import setup_scheduler
from database.database import engine, Base, SessionLocal
from database.models import Service, Provider

def seed_db():
    db = SessionLocal()
    if not db.query(Service).first():
        db.add_all([
            Service(name="Консультация", price=1000, duration=30),
            Service(name="Диагностика", price=2500, duration=60),
            Service(name="Ремонт", price=5000, duration=120)
        ])
    if not db.query(Provider).first():
        db.add_all([
            Provider(name="Иван (Специалист 1)"),
            Provider(name="Анна (Специалист 2)"),
            Provider(name="Сергей (Специалист 3)")
        ])
    db.commit()
    db.close()

def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    
    if not token or token == "твой_токен_здесь":
        print("Пожалуйста, установите BOT_TOKEN в файле .env")
        return

    # Создаем таблицы в БД
    Base.metadata.create_all(bind=engine)
    
    # Заполняем БД тестовыми данными (если пустая)
    seed_db()
    
    # Инициализация приложения
    application = Application.builder().token(token).build()
    
    # Добавление обработчиков
    for handler in get_main_handlers():
        application.add_handler(handler)
    
    # Настройка планировщика уведомлений
    setup_scheduler(application)
    
    # Запуск бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
