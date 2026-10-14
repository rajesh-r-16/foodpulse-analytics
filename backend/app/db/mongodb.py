from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import MONGODB_URI, DATABASE_NAME

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[DATABASE_NAME]

def check_connection():
    client.admin.command("ping")

def create_indexes():
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.orders.create_index([("order_date", DESCENDING)])
    db.orders.create_index([("status", ASCENDING)])
    db.orders.create_index([("restaurant_id", ASCENDING)])
    db.customers.create_index([("email", ASCENDING)], unique=True, sparse=True)
    db.restaurants.create_index([("name", ASCENDING)])
    db.menu_items.create_index([("restaurant_id", ASCENDING)])
    db.deliveries.create_index([("order_id", ASCENDING)], unique=True, sparse=True)
