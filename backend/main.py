from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import models, schemas, billing
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tiffin Service")

@app.post("/api/v1/subscriptions")
def create_subscription(sub: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    new_sub = models.Subscription(**sub.dict())
    db.add(new_sub)
    db.commit()
    return new_sub

@app.get("/api/v1/subscriptions")
def search_subscriptions(phone: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Subscription).join(models.User)
    if phone:
        query = query.filter(models.User.phone.like(f"%{phone}%"))
    return query.all()

@app.post("/api/v1/subscriptions/{sub_id}/pause")
def pause_subscription(sub_id: int, req: schemas.PauseRequest, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    log = models.PauseLog(subscription_id=sub.id, pause_start=req.pause_start, pause_end=req.pause_end)
    sub.status = models.SubscriptionStatus.PAUSED
    db.add(log)
    db.commit()
    return {"message": "Paused successfully"}

@app.get("/api/v1/subscriptions/{sub_id}/bill")
def get_bill(sub_id: int, year: int, month: int, db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    return billing.calculate_monthly_bill(sub, year, month)