import os
from typing import Optional
from datetime import date, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models, schemas, billing
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DailyBite Tiffin Management API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=FileResponse)
def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="index.html not found in backend/static/")

@app.post("/api/v1/subscriptions", response_model=schemas.SubscriptionResponse)
def create_subscription(sub: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(id=sub.user_id).first()
    if not user:
        user = models.User(name="Default Customer", phone="9876543210")
        db.add(user)
        db.commit()
        db.refresh(user)
        sub.user_id = user.id

    new_sub = models.Subscription(user_id=sub.user_id, monthly_rate=sub.monthly_rate)
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

@app.get("/api/v1/subscriptions")
def search_subscriptions(phone: Optional[str] = None, db: Session = Depends(get_db)):
    if phone:
        results = db.query(models.Subscription).join(models.User).filter(models.User.phone.contains(phone)).all()
        if not results:
            raise HTTPException(status_code=404, detail=f"No subscription found for phone: {phone}")
        return results
    return db.query(models.Subscription).all()

@app.post("/api/v1/subscriptions/{sub_id}/pause")
def pause_subscription(sub_id: int, req: schemas.PauseRequest, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
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
    return {"message": "Success: Subscription paused"}

@app.post("/api/v1/subscriptions/{sub_id}/resume")
def resume_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")
    
    sub.status = models.SubscriptionStatus.ACTIVE
    db.commit()
    return {"message": "Success: Subscription resumed"}

@app.get("/api/v1/subscriptions/{sub_id}/bill")
def get_bill(sub_id: int, year: int = 2026, month: int = 9, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")
    
    bill_data = billing.calculate_monthly_bill(sub, year, month)
    user = db.query(models.User).filter_by(id=sub.user_id).first()
    phone_number = user.phone if user else "N/A"
    
    # Calculate pay-before date (5th of the following month)
    due_date = date(year, month, 1) + timedelta(days=32)
    pay_before = date(due_date.year, due_date.month, 5).strftime("%d-%b-%Y")

    return {
        "subscription_id": sub.id,
        "phone_number": phone_number,
        "total_amount_due": f"₹{bill_data['total_bill']}",
        "pay_before": pay_before,
        "message": f"Bill generated for {phone_number}. Total amount payable is ₹{bill_data['total_bill']}. Please pay before {pay_before}."
    }