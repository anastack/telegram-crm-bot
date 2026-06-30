# Telegram CRM Bot & Mini App

Проект включает в себя Telegram-бота для записи клиентов и Mini App для администраторов. 
Разработано с использованием Python (FastAPI, python-telegram-bot, SQLAlchemy) и HTML/CSS/JS.

## Запуск локально
1. Установите зависимости: `pip install -r requirements.txt`
2. Скопируйте `.env.example` в `.env` и заполните данные.
3. Запустите: `python backend/main.py`

## Деплой на Railway
Проект полностью готов к деплою на Railway через GitHub. 
Точка входа настроена в файле `Procfile`.
Не забудьте добавить переменные `BOT_TOKEN`, `ADMIN_IDS` и `WEBAPP_URL` в настройках Variables в Railway.
