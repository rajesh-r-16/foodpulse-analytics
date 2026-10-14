from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from app.db.mongodb import db
from app.schemas import OrderCreate, OrderUpdate
from app.core.security import get_current_user
from app.utils import serialize, now_utc
import re

router = APIRouter(prefix="/api/orders", tags=["Orders"], dependencies=[Depends(get_current_user)])

@router.get("")
def list_orders(search: str = "", status: str = "", city: str = "", limit: int = Query(500, ge=1, le=2500), skip: int = 0):
    query = {}
    if status: query["status"] = status
    if city: query["city"] = city
    if search:
        query["$or"] = [{"customer_name": {"$regex": search, "$options": "i"}}, {"restaurant_name": {"$regex": search, "$options": "i"}}, {"order_code": {"$regex": search, "$options": "i"}}]
    docs = db.orders.find(query).sort("order_date", -1).skip(skip).limit(limit)
    return {"items": [serialize(x) for x in docs], "total": db.orders.count_documents(query)}

@router.post("")
def create_order(payload: OrderCreate):
    doc = payload.model_dump()
    # Keep the Customers module in sync whenever a new order introduces a customer.
    customer_name = " ".join((doc.get("customer_name") or "").split()).strip()
    customer_email = (doc.get("customer_email") or "").strip().lower() or None
    city = (doc.get("city") or "Bengaluru").strip()
    customer_query = {"email": customer_email} if customer_email else {"name": {"$regex": "^" + re.escape(customer_name) + "$", "$options": "i"}, "city": city}
    existing_customer = db.customers.find_one(customer_query) if customer_name else None
    if existing_customer:
        customer_id = str(existing_customer["_id"])
        customer_updates = {"name": customer_name, "city": city}
        if customer_email:
            customer_updates["email"] = customer_email
        db.customers.update_one({"_id": existing_customer["_id"]}, {"$set": customer_updates})
    else:
        customer_doc = {"name": customer_name, "email": customer_email, "phone": None, "city": city, "created_at": now_utc(), "source": "order"}
        inserted_customer = db.customers.insert_one(customer_doc)
        customer_id = str(inserted_customer.inserted_id)
    doc.update({"customer_id": customer_id, "customer_name": customer_name, "customer_email": customer_email, "city": city,
                "order_code": "FP-" + now_utc().strftime("%y%m%d%H%M%S%f")[-10:], "order_date": now_utc(), "created_at": now_utc()})
    result = db.orders.insert_one(doc)
    return serialize(db.orders.find_one({"_id": result.inserted_id}))

@router.get("/{order_id}")
def get_order(order_id: str):
    if not ObjectId.is_valid(order_id): raise HTTPException(400, "Invalid order id")
    doc = db.orders.find_one({"_id": ObjectId(order_id)})
    if not doc: raise HTTPException(404, "Order not found")
    return serialize(doc)

@router.patch("/{order_id}")
def update_order(order_id: str, payload: OrderUpdate):
    if not ObjectId.is_valid(order_id): raise HTTPException(400, "Invalid order id")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates: raise HTTPException(400, "No fields provided to update")
    result = db.orders.update_one({"_id": ObjectId(order_id)}, {"$set": updates})
    if not result.matched_count: raise HTTPException(404, "Order not found")
    return serialize(db.orders.find_one({"_id": ObjectId(order_id)}))

@router.delete("/{order_id}")
def delete_order(order_id: str):
    if not ObjectId.is_valid(order_id): raise HTTPException(400, "Invalid order id")
    result = db.orders.delete_one({"_id": ObjectId(order_id)})
    if not result.deleted_count: raise HTTPException(404, "Order not found")
    return {"message": "Order deleted"}
