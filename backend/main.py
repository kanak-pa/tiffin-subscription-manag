import os
import re
from datetime import date, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import billing
import models
import schemas
from database import engine, get_db

# Recreate tables to apply model schema cleanly
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


# --- SUBSCRIPTION ROUTING ---

@app.post("/api/v1/subscriptions", response_model=schemas.SubscriptionResponse)
def create_subscription(sub: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(id=sub.user_id).first()
    if not user:
        user = models.User(name="Default Customer", phone=f"98765{sub.user_id:05d}")
        db.add(user)
        db.commit()
        db.refresh(user)

    new_sub = models.Subscription(
        user_id=user.id, 
        monthly_rate=sub.monthly_rate,
        status=models.SubscriptionStatus.ACTIVE
    )
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
    db.refresh(sub)
    return {"message": f"Success: Subscription #{sub.id} set to PAUSED", "status": sub.status}


@app.post("/api/v1/subscriptions/{sub_id}/resume")
def resume_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")

    sub.status = models.SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(sub)
    return {"message": f"Success: Subscription #{sub.id} set to ACTIVE", "status": sub.status}


@app.get("/api/v1/subscriptions/{sub_id}/bill")
def get_bill(sub_id: int, year: int = 2026, month: int = 9, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription ID not found")

    bill_data = billing.calculate_monthly_bill(sub, year, month)
    user = db.query(models.User).filter_by(id=sub.user_id).first()
    phone_number = user.phone if user else "N/A"

    due_date = date(year, month, 1) + timedelta(days=32)
    pay_before = date(due_date.year, due_date.month, 5).strftime("%d-%b-%Y")

    return {
        "subscription_id": sub.id,
        "phone_number": phone_number,
        "total_amount_due": f"₹{bill_data['total_bill']}",
        "pay_before": pay_before
    }


# --- TWIST 1: CLOCK & OUTBOX (T1) ---

@app.post("/clock")
def trigger_clock(current_date: date, db: Session = Depends(get_db)):
    # Check if weekday (0 = Monday, ..., 4 = Friday)
    if current_date.weekday() < 5:
        active_subs = db.query(models.Subscription).filter(
            models.Subscription.status == models.SubscriptionStatus.ACTIVE
        ).all()
        
        for sub in active_subs:
            # Check if current_date falls in pause range
            is_paused = any(
                p.pause_start <= current_date <= p.pause_end
                for p in sub.pause_logs
            )
            if not is_paused:
                user = db.query(models.User).filter_by(id=sub.user_id).first()
                if user:
                    msg = f"Good morning {user.name}, your tiffin delivery is scheduled for today!"
                    outbox_entry = models.OutboxNotification(
                        recipient_phone=user.phone, 
                        message=msg
                    )
                    db.add(outbox_entry)
        db.commit()
        return {"message": f"Clock processed for weekday: {current_date}"}
    
    return {"message": f"Clock processed for weekend: {current_date} (No deliveries)"}


@app.get("/outbox")
def get_outbox(db: Session = Depends(get_db)):
    return db.query(models.OutboxNotification).all()


# --- TWIST 2: MID-CYCLE TRANSFER (T6) ---

@app.post("/api/v1/subscriptions/{sub_id}/transfer")
def transfer_subscription(
    sub_id: int, 
    new_user_id: int, 
    effective_date: date, 
    db: Session = Depends(get_db)
):
    sub = db.query(models.Subscription).filter_by(id=sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    target_user = db.query(models.User).filter_by(id=new_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user ID does not exist")

    transfer = models.SubscriptionTransfer(
        subscription_id=sub.id,
        from_user_id=sub.user_id,
        to_user_id=new_user_id,
        effective_date=effective_date
    )
    db.add(transfer)
    
    # Ownership transfers to new user
    sub.user_id = new_user_id
    db.commit()

    return {"message": f"Subscription #{sub.id} successfully transferred to User ID #{new_user_id}"}


# --- TWIST 3: MESSY DATA IMPORT (T4) ---

@app.post("/import")
def import_customers(records: List[dict] = Body(...), db: Session = Depends(get_db)):
    report = {"imported": 0, "deduped": 0, "rejected": 0}
    seen_phones = set()

    for item in records:
        name = item.get("name")
        raw_phone = item.get("phone")

        if not name or not raw_phone or str(name).strip() == "":
            report["rejected"] += 1
            continue

        # Clean non-digit characters
        phone = re.sub(r"\D", "", str(raw_phone))
        if len(phone) < 10:
            report["rejected"] += 1
            continue

        # Check existing in session or Database
        if phone in seen_phones or db.query(models.User).filter_by(phone=phone).first():
            report["deduped"] += 1
            continue

        seen_phones.add(phone)

        # Create user & initial active subscription
        user = models.User(name=str(name).strip(), phone=phone)
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

        report["imported"] += 1

    return report