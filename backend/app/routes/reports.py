from datetime import datetime, time, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.mongodb import db
from app.core.security import get_current_user
from app.utils import serialize

router = APIRouter(prefix="/api/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])

@router.get("/orders")
def order_report(
    from_date: Optional[str] = Query(default=None, description="Inclusive date in YYYY-MM-DD format"),
    to_date: Optional[str] = Query(default=None, description="Inclusive date in YYYY-MM-DD format"),
    status: str = "",
    restaurant: str = "",
    limit: int = Query(default=500, ge=1, le=2000),
    skip: int = Query(default=0, ge=0),
):
    query = {}
    date_filter = {}
    try:
        if from_date:
            start = datetime.combine(datetime.strptime(from_date, "%Y-%m-%d").date(), time.min).replace(tzinfo=timezone.utc)
            date_filter["$gte"] = start
        if to_date:
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date() + timedelta(days=1)
            date_filter["$lt"] = datetime.combine(end_date, time.min).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD format")
    if date_filter:
        query["order_date"] = date_filter
    if status:
        query["status"] = status
    if restaurant.strip():
        query["restaurant_name"] = {"$regex": restaurant.strip(), "$options": "i"}
    total = db.orders.count_documents(query)
    docs = db.orders.find(query).sort("order_date", -1).skip(skip).limit(limit)
    items = [serialize(doc) for doc in docs]
    revenue_pipeline = [{"$match": {**query, "status": {"$ne": "cancelled"}}}, {"$group": {"_id": None, "revenue": {"$sum": "$total_amount"}}}]
    revenue_rows = list(db.orders.aggregate(revenue_pipeline))
    revenue = round(float(revenue_rows[0].get("revenue", 0)), 2) if revenue_rows else 0
    return {"items": items, "total": total, "revenue": revenue, "limit": limit, "skip": skip}

@router.get("/summary")
def report_summary(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    query = {}
    date_filter = {}
    try:
        if from_date:
            date_filter["$gte"] = datetime.combine(datetime.strptime(from_date, "%Y-%m-%d").date(), time.min).replace(tzinfo=timezone.utc)
        if to_date:
            date_filter["$lt"] = datetime.combine(datetime.strptime(to_date, "%Y-%m-%d").date() + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD format")
    if date_filter:
        query["order_date"] = date_filter
    pipeline = [{"$match": query}, {"$group": {"_id": "$status", "orders": {"$sum": 1}, "revenue": {"$sum": {"$cond": [{"$ne": ["$status", "cancelled"]}, {"$ifNull": ["$total_amount", 0]}, 0]}}}}, {"$sort": {"orders": -1}}]
    statuses = list(db.orders.aggregate(pipeline))
    return {"total_orders": db.orders.count_documents(query), "by_status": [{"status": x.get("_id") or "unknown", "orders": x["orders"], "revenue": round(float(x["revenue"]), 2)} for x in statuses], "generated_at": datetime.now(timezone.utc).isoformat()}
