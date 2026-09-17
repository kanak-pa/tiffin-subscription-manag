import os
import re
from datetime import date, timedelta
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import billing
import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DailyBite Tiffin Management System")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Page Routes ---
@app.get("/", response_class=FileResponse)
def root_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/login", response_class=FileResponse)
def login_page():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/dashboard", response_class=FileResponse)
def dashboard_page():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.get("/bill", response_class=FileResponse)
def bill_page():
    return FileResponse(os.path.join(STATIC_DIR, "bill.html"))

# --- Auth APIs ---
@app.post("/api/v1/auth/register", response_model=schemas.UserResponse)
def register_user(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    clean_phone = re.sub(r"\D", "", user_data.phone)
    if len(clean_phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    existing = db.query(models.User).filter_by(phone=clean_phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    user = models.User(name=user_data.name, phone=clean_phone)
    db.add(user)
    db.commit()
    db.refresh(user)

    sub = models.Subscription(
        user_id=user.id,
        monthly_rate=3000.0,
        status=models.SubscriptionStatus.ACTIVE
    )
    db.add(sub)
    db.commit()
    
    return user

@app.post("/api/v1/auth/login")
def login_user(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    clean_phone = re.sub(r"\D", "", credentials.phone)
    user = db.query(models.User).filter_by(phone=clean_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    
    sub = db.query(models.Subscription).filter_by(user_id=user.id).first()
    return {
        "user_id": user.id,
        "name": user.name,
        "phone": user.phone,
        "subscription_id": sub.id if sub else None
    }

# --- Subscription & Billing APIs ---
@app.get("/api/v1/subscriptions/{sub_id}")
def get_subscription_details(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "status": sub.status,
        "monthly_rate": sub.monthly_rate
    }

@app.post("/api/v1/subscriptions/{sub_id}/pause")
def pause_subscription(sub_id: int, req: schemas.PauseRequest, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")

    log = models.PauseLog(
        subscription_id=sub.id,
        pause_start=req.pause_start,
        pause_end=req.pause_end
    )
    sub.status = models.SubscriptionStatus.PAUSED
    db.add(log)
    db.commit()
    return {"message": "Subscription set to PAUSED successfully", "status": sub.status}

@app.post("/api/v1/subscriptions/{sub_id}/resume")
def resume_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")

    sub.status = models.SubscriptionStatus.ACTIVE
    db.commit()
    return {"message": "Subscription set to ACTIVE successfully", "status": sub.status}

@app.get("/api/v1/subscriptions/{sub_id}/bill")
def get_bill(sub_id: int, year: int = 2026, month: int = 9, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")

    bill_data = billing.calculate_monthly_bill(sub, year, month)
    user = db.query(models.User).filter_by(id=sub.user_id).first()

    due_date = date(year, month, 1) + timedelta(days=32)
    pay_before = date(due_date.year, due_date.month, 5).strftime("%d-%b-%Y")

    return {
        "subscription_id": sub.id,
        "customer_name": user.name if user else "N/A",
        "phone_number": user.phone if user else "N/A",
        "month_year": f"{month}/{year}",
        "days_in_month": bill_data['days_in_month'],
        "paused_days": bill_data['paused_days'],
        "active_days": bill_data['active_days'],
        "total_amount_due": f"₹{bill_data['total_bill']}",
        "pay_before": pay_before
    }