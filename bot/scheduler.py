import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.database import SessionLocal
from database.models import Appointment
from datetime import datetime, timedelta
from telegram.ext import Application

async def send_reminders(app: Application):
    db = SessionLocal()
    now = datetime.now()
    two_hours_later = now + timedelta(hours=2)
    
    # Находим записи, которые начнутся ровно через 2 часа (+- 1 минута)
    appointments = db.query(Appointment).filter(
        Appointment.status == "active",
        Appointment.date_time >= two_hours_later - timedelta(minutes=1),
        Appointment.date_time <= two_hours_later + timedelta(minutes=1)
    ).all()
    
    for apt in appointments:
        try:
            await app.bot.send_message(
                chat_id=apt.user.telegram_id,
                text=f"Напоминание: У вас запись на услугу '{apt.service.name}' сегодня в {apt.date_time.strftime('%H:%M')}!"
            )
        except Exception as e:
            print(f"Failed to send reminder to {apt.user.telegram_id}: {e}")
            
    db.close()

def setup_scheduler(app: Application):
    scheduler = AsyncIOScheduler()
    # Проверяем каждую минуту
    scheduler.add_job(send_reminders, 'cron', minute='*', args=[app])
    scheduler.start()
