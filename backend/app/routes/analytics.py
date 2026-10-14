from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from app.db.mongodb import db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"], dependencies=[Depends(get_current_user)])

@router.get("/overview")
def overview():
    orders = db.orders
    total = orders.count_documents({})
    delivered = orders.count_documents({"status": "delivered"})
    cancelled = orders.count_documents({"status": "cancelled"})
    revenue_pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$total_amount"}, "avg_order_value": {"$avg": "$total_amount"}}}
    ]
    rev = list(orders.aggregate(revenue_pipeline))
    revenue = round(float(rev[0].get("revenue", 0)), 2) if rev else 0
    aov = round(float(rev[0].get("avg_order_value", 0)), 2) if rev else 0
    times = [x["delivery_minutes"] for x in orders.find({"delivery_minutes": {"$type": "number"}, "status": "delivered"}, {"delivery_minutes": 1})]
    avg_delivery = round(sum(times)/len(times), 1) if times else 0
    return {
        "total_orders": total, "revenue": revenue, "average_order_value": aov,
        "delivered_orders": delivered, "cancelled_orders": cancelled,
        "cancellation_rate": round(cancelled / total * 100, 1) if total else 0,
        "average_delivery_minutes": avg_delivery,
        "active_restaurants": db.restaurants.count_documents({"is_active": True}),
        "total_customers": db.customers.count_documents({})
    }

@router.get("/revenue")
def revenue_series():
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}}, "revenue": {"$sum": "$total_amount"}, "orders": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    return [{"date": x["_id"], "revenue": round(float(x["revenue"]), 2), "orders": x["orders"]} for x in db.orders.aggregate(pipeline)]

@router.get("/orders-by-status")
def orders_by_status():
    pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    return [{"status": x["_id"], "count": x["count"]} for x in db.orders.aggregate(pipeline)]

@router.get("/top-restaurants")
def top_restaurants():
    pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": "$restaurant_name", "orders": {"$sum": 1}, "revenue": {"$sum": "$total_amount"}}},
        {"$sort": {"revenue": -1}}, {"$limit": 10}
    ]
    return [{"restaurant": x["_id"], "orders": x["orders"], "revenue": round(float(x["revenue"]), 2)} for x in db.orders.aggregate(pipeline)]

@router.get("/popular-items")
def popular_items():
    pipeline = [
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.name", "quantity": {"$sum": {"$ifNull": ["$items.quantity", 1]}}, "revenue": {"$sum": {"$multiply": [{"$ifNull": ["$items.quantity", 1]}, {"$ifNull": ["$items.price", 0]}]}}}},
        {"$sort": {"quantity": -1}}, {"$limit": 10}
    ]
    return [{"item": x["_id"] or "Unknown", "quantity": x["quantity"], "revenue": round(float(x["revenue"]), 2)} for x in db.orders.aggregate(pipeline)]

@router.get("/insights")
def insights():
    total = db.orders.count_documents({})
    cancelled = db.orders.count_documents({"status": "cancelled"})
    delayed = db.orders.count_documents({"status": "delivered", "delivery_minutes": {"$gt": 45}})
    avg = list(db.orders.aggregate([{"$match": {"status": {"$ne": "cancelled"}}}, {"$group": {"_id": None, "avg": {"$avg": "$total_amount"}}}]))
    avg_value = float(avg[0]["avg"]) if avg else 0
    result = []
    if total and cancelled / total >= 0.1:
        result.append({"level": "warning", "title": "Cancellation rate is elevated", "detail": f"{cancelled} of {total} orders were cancelled."})
    if delayed:
        result.append({"level": "warning", "title": "Delivery delays detected", "detail": f"{delayed} delivered orders took more than 45 minutes."})
    if avg_value:
        result.append({"level": "info", "title": "Average order value", "detail": f"Average non-cancelled order value is ₹{avg_value:.2f}."})
    if not result:
        result.append({"level": "success", "title": "No major issues detected", "detail": "Add more orders to generate richer insights."})
    return result
