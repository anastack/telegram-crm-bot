from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Appointment, User, Service, Provider
from datetime import datetime

router = APIRouter(prefix="/api")

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_appointments = db.query(Appointment).count()
    total_clients = db.query(User).count()
    active_appointments = db.query(Appointment).filter(Appointment.status == "active").count()
    return {
        "total_appointments": total_appointments,
        "total_clients": total_clients,
        "active_appointments": active_appointments
    }

@router.get("/appointments")
def get_appointments(db: Session = Depends(get_db)):
    appointments = db.query(Appointment).all()
    result = []
    for app in appointments:
        result.append({
            "id": app.id,
            "client_name": app.user.name,
            "service": app.service.name,
            "provider": app.provider.name,
            "date": app.date_time.strftime('%Y-%m-%d'),
            "time": app.date_time.strftime('%H:%M'),
            "status": app.status
        })
    return result

@router.post("/appointments/{app_id}/cancel")
def cancel_appointment(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Appointment).filter(Appointment.id == app_id).first()
    if app:
        app.status = "cancelled"
        db.commit()
        return {"success": True}
    return {"success": False, "error": "Not found"}

@router.get("/clients")
def get_clients(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "telegram_id": user.telegram_id,
        })
    return result
