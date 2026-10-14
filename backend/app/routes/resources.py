from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from app.db.mongodb import db
from app.core.security import get_current_user
from app.schemas import RestaurantCreate, CustomerCreate, MenuItemCreate, DeliveryCreate, ReviewCreate
from app.utils import serialize, now_utc

router = APIRouter(prefix="/api", tags=["Business data"], dependencies=[Depends(get_current_user)])

def listing(collection, query=None, limit=5000):
    return [serialize(x) for x in collection.find(query or {}).sort("_id", -1).limit(limit)]

@router.get("/restaurants")
def restaurants(search: str = "", city: str = ""):
    q = {}
    if search: q["$or"] = [{"name": {"$regex": search, "$options": "i"}}, {"cuisine": {"$regex": search, "$options": "i"}}]
    if city: q["city"] = city
    return {"items": listing(db.restaurants, q)}

@router.post("/restaurants")
def create_restaurant(payload: RestaurantCreate):
    doc = payload.model_dump()
    result = db.restaurants.insert_one(doc)
    return serialize(db.restaurants.find_one({"_id": result.inserted_id}))

@router.delete("/restaurants/{item_id}")
def delete_restaurant(item_id: str):
    if not ObjectId.is_valid(item_id): raise HTTPException(400, "Invalid restaurant id")
    result = db.restaurants.delete_one({"_id": ObjectId(item_id)})
    if not result.deleted_count: raise HTTPException(404, "Restaurant not found")
    return {"message": "Restaurant deleted"}

@router.get("/customers")
def customers(search: str = ""):
    q = {"name": {"$regex": search, "$options": "i"}} if search else {}
    return {"items": listing(db.customers, q)}

@router.post("/customers")
def create_customer(payload: CustomerCreate):
    doc = payload.model_dump()
    result = db.customers.insert_one(doc)
    return serialize(db.customers.find_one({"_id": result.inserted_id}))

@router.get("/menu")
def menu(restaurant_id: str = "", category: str = ""):
    q = {}
    if restaurant_id: q["restaurant_id"] = restaurant_id
    if category: q["category"] = category
    return {"items": listing(db.menu_items, q)}

@router.post("/menu")
def create_menu_item(payload: MenuItemCreate):
    doc = payload.model_dump()
    result = db.menu_items.insert_one(doc)
    return serialize(db.menu_items.find_one({"_id": result.inserted_id}))

@router.patch("/menu/{item_id}/availability")
def toggle_menu_item(item_id: str):
    if not ObjectId.is_valid(item_id): raise HTTPException(400, "Invalid menu item id")
    doc = db.menu_items.find_one({"_id": ObjectId(item_id)})
    if not doc: raise HTTPException(404, "Menu item not found")
    db.menu_items.update_one({"_id": ObjectId(item_id)}, {"$set": {"is_available": not doc.get("is_available", True)}})
    return serialize(db.menu_items.find_one({"_id": ObjectId(item_id)}))

@router.get("/deliveries")
def deliveries():
    return {"items": listing(db.deliveries)}

@router.post("/deliveries")
def create_delivery(payload: DeliveryCreate):
    doc = payload.model_dump()
    doc["assigned_at"] = now_utc()
    result = db.deliveries.insert_one(doc)
    return serialize(db.deliveries.find_one({"_id": result.inserted_id}))

@router.patch("/deliveries/{delivery_id}/status")
def update_delivery_status(delivery_id: str, payload: dict):
    if not ObjectId.is_valid(delivery_id):
        raise HTTPException(400, "Invalid delivery id")
    allowed = {"assigned", "picked_up", "out_for_delivery", "delivered", "cancelled", "failed"}
    status = str(payload.get("status", "")).strip().lower()
    if status not in allowed:
        raise HTTPException(422, f"Status must be one of: {', '.join(sorted(allowed))}")
    delivery = db.deliveries.find_one({"_id": ObjectId(delivery_id)})
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    update = {"status": status, "status_updated_at": now_utc()}
    if status == "delivered" and not delivery.get("delivery_minutes"):
        update["delivery_minutes"] = 30
    db.deliveries.update_one({"_id": ObjectId(delivery_id)}, {"$set": update})
    # Keep the related order status in sync when its order code or Mongo id is known.
    order_id = delivery.get("order_id")
    order_status = {"assigned": "confirmed", "picked_up": "out_for_delivery", "out_for_delivery": "out_for_delivery", "delivered": "delivered", "cancelled": "cancelled", "failed": "cancelled"}.get(status)
    if order_id and order_status:
        order_filter = {"$or": [{"order_code": order_id}]}
        if ObjectId.is_valid(str(order_id)):
            order_filter["$or"].append({"_id": ObjectId(str(order_id))})
        db.orders.update_one(order_filter, {"$set": {"status": order_status}})
    return serialize(db.deliveries.find_one({"_id": ObjectId(delivery_id)}))

@router.get("/reviews")
def reviews():
    return {"items": listing(db.reviews)}

@router.post("/reviews")
def create_review(payload: ReviewCreate):
    doc = payload.model_dump()
    doc["created_at"] = now_utc()
    result = db.reviews.insert_one(doc)
    return serialize(db.reviews.find_one({"_id": result.inserted_id}))
