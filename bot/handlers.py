from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database.database import SessionLocal
from database.models import User, Service, Provider, Appointment
from datetime import datetime, timedelta
import os
from bot.ai_assistant import process_user_message

# Получаем ID админов и ссылку на Mini App из .env
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://test.up.railway.app")

# Этапы ConversationHandler для процесса записи
(
    SELECT_SERVICE,
    SELECT_PROVIDER,
    SELECT_DATE,
    SELECT_TIME,
    CONFIRM_APPOINTMENT
) = range(5)

AI_CHAT = 10


# ----------------- ОСНОВНОЕ МЕНЮ (Reply) -----------------

def get_main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton("📅 Записаться"), KeyboardButton("📝 Мои записи")],
        [KeyboardButton("🤖 ИИ-помощник"), KeyboardButton("ℹ️ О нас")]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton("⚙️ Админ-панель", web_app=WebAppInfo(url=WEBAPP_URL))])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    name = update.message.from_user.full_name
    
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        new_user = User(telegram_id=user_id, name=name)
        db.add(new_user)
        db.commit()
    db.close()

    text = (
        f"👋 Привет, {name}!\n\n"
        "Добро пожаловать в нашу CRM-систему.\n"
        "Выберите нужное действие в меню ниже:"
    )
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "ℹ️ *О нас*\n\n"
        "Мы — лучший сервис для предоставления услуг!\n"
        "Работаем каждый день, чтобы радовать вас. Ждём в гости!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == update.message.from_user.id).first()
    if not user:
        db.close()
        return
        
    appointments = db.query(Appointment).filter(Appointment.user_id == user.id, Appointment.status == "active").all()
    
    if not appointments:
        await update.message.reply_text("У вас пока нет активных записей 😔", reply_markup=get_main_keyboard(update.message.from_user.id))
    else:
        text = "📋 *Ваши предстоящие записи:*\n\n"
        for app in appointments:
            date_str = app.date_time.strftime('%d.%m.%Y в %H:%M')
            text += f"✂️ *Услуга:* {app.service.name}\n👤 *Исполнитель:* {app.provider.name}\n📅 *Дата:* {date_str}\n➖➖➖➖➖➖\n"
        
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(update.message.from_user.id))
    db.close()

# ----------------- ПРОЦЕСС ЗАПИСИ (Inline) -----------------

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = SessionLocal()
    services = db.query(Service).all()
    db.close()
    
    if not services:
        await update.message.reply_text("К сожалению, список услуг пока пуст. Возвращайтесь позже!")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton(f"🔹 {s.name} ({s.price}₽, {s.duration} мин)", callback_data=f"service_{s.id}")] for s in services]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await update.message.reply_text("Какая услуга вас интересует?\n\nВыберите из списка:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_SERVICE

async def select_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Запись отменена 🚫")
        return ConversationHandler.END
        
    service_id = int(query.data.split("_")[1])
    context.user_data['service_id'] = service_id
    
    db = SessionLocal()
    providers = db.query(Provider).all()
    db.close()
    
    if not providers:
        await query.edit_message_text("Нет доступных исполнителей.")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton(f"👨‍💼 {p.name}", callback_data=f"provider_{p.id}")] for p in providers]
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_services"), InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.edit_message_text("Отлично! К кому бы вы хотели записаться?", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_PROVIDER

async def back_to_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    services = db.query(Service).all()
    db.close()
    
    keyboard = [[InlineKeyboardButton(f"🔹 {s.name} ({s.price}₽, {s.duration} мин)", callback_data=f"service_{s.id}")] for s in services]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.edit_message_text("Какая услуга вас интересует?\n\nВыберите из списка:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_SERVICE

async def select_provider(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("Запись отменена 🚫")
        return ConversationHandler.END
    
    if query.data == "back_to_services":
        return await back_to_services(update, context)
        
    provider_id = int(query.data.split("_")[1])
    context.user_data['provider_id'] = provider_id
    
    # Делаем читабельные даты (например: 25.10.2023)
    today = datetime.today()
    dates = [today + timedelta(days=i) for i in range(1, 4)]
    
    keyboard = []
    for d in dates:
        date_nice = d.strftime("%d.%m.%Y")
        date_val = d.strftime("%Y-%m-%d")
        keyboard.append([InlineKeyboardButton(f"🗓 {date_nice}", callback_data=f"date_{date_val}")])
        
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.edit_message_text("Выберите удобную дату для записи:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DATE

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Запись отменена 🚫")
        return ConversationHandler.END
        
    selected_date = query.data.split("_")[1]
    context.user_data['date'] = selected_date
    
    # Красивый вывод выбранной даты
    dt = datetime.strptime(selected_date, "%Y-%m-%d")
    date_nice = dt.strftime("%d.%m.%Y")
    
    times = ["10:00", "12:00", "14:00", "16:00"]
    keyboard = [[InlineKeyboardButton(f"⏰ {t}", callback_data=f"time_{t}")] for t in times]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    await query.edit_message_text(f"Дата: *{date_nice}*\n\nВыберите доступное время:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Запись отменена 🚫")
        return ConversationHandler.END
        
    selected_time = query.data.split("_")[1]
    context.user_data['time'] = selected_time
    
    date_str = context.user_data['date']
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_nice = dt.strftime("%d.%m.%Y")
    
    text = (
        "📌 *Подтверждение записи:*\n\n"
        f"📅 *Дата:* {date_nice}\n"
        f"⏰ *Время:* {selected_time}\n\n"
        "Всё верно?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_APPOINTMENT

async def confirm_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cancel":
        await query.edit_message_text("Запись отменена 🚫")
        return ConversationHandler.END
        
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
    
    date_time_str = f"{context.user_data['date']} {context.user_data['time']}"
    appointment_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
    
    new_app = Appointment(
        user_id=user.id,
        service_id=context.user_data['service_id'],
        provider_id=context.user_data['provider_id'],
        date_time=appointment_dt
    )
    db.add(new_app)
    db.commit()
    db.close()
    
    await query.edit_message_text("🎉 *Ваша запись успешно подтверждена!*\n\nЖдем вас! Напомним о визите за 2 часа.", parse_mode="Markdown")
    
    # Отправляем отдельное сообщение с основным меню, чтобы убедиться, что клавиатура на месте
    await context.bot.send_message(
        chat_id=query.from_user.id, 
        text="Вы вернулись в главное меню.", 
        reply_markup=get_main_keyboard(query.from_user.id)
    )
    return ConversationHandler.END

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
    if update.callback_query:
        await update.callback_query.edit_message_text("Запись отменена 🚫")
    else:
        await update.message.reply_text("Запись отменена 🚫", reply_markup=get_main_keyboard(user_id))
    return ConversationHandler.END

def get_ai_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Выйти из чата с ИИ")]], resize_keyboard=True)

async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "🤖 Привет! Я умный помощник.\n\nВы можете спросить меня об услугах, мастерах, или попросить записать вас на прием.\nНапишите ваш вопрос (или нажмите 'Выйти', чтобы вернуться в меню):"
    await update.message.reply_text(text, reply_markup=get_ai_keyboard())
    return AI_CHAT

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Отправляем индикатор набора текста
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    
    # Получаем ответ от ИИ
    reply_text = await process_user_message(user_id, text)
    
    # Отправляем ответ пользователю
    await update.message.reply_text(reply_text, reply_markup=get_ai_keyboard())
    return AI_CHAT

async def stop_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Вы вышли из режима ИИ-помощника.", reply_markup=get_main_keyboard(update.message.from_user.id))
    return ConversationHandler.END


# ----------------- СБОРКА ОБРАБОТЧИКОВ -----------------

def get_conversation_handler():
    # Обработчик диалога только для процесса записи
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📅 Записаться$"), start_booking)],
        states={
            SELECT_SERVICE: [CallbackQueryHandler(select_service)],
            SELECT_PROVIDER: [CallbackQueryHandler(select_provider)],
            SELECT_DATE: [CallbackQueryHandler(select_date)],
            SELECT_TIME: [CallbackQueryHandler(select_time)],
            CONFIRM_APPOINTMENT: [CallbackQueryHandler(confirm_appointment)]
        },
        fallbacks=[CommandHandler("cancel", cancel_booking)]
    )

def get_ai_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🤖 ИИ-помощник$"), start_ai_chat)],
        states={
            AI_CHAT: [MessageHandler(filters.TEXT & ~filters.Regex("^❌ Выйти из чата с ИИ$"), handle_ai_message)]
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Выйти из чата с ИИ$"), stop_ai_chat)]
    )

def get_main_handlers():
    return [
        CommandHandler("start", start),
        MessageHandler(filters.Regex("^📝 Мои записи$"), my_appointments),
        MessageHandler(filters.Regex("^ℹ️ О нас$"), about_us),
        get_conversation_handler(),
        get_ai_conversation_handler()
    ]
