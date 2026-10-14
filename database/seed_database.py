"""Seed FoodPulse Analytics with a large, reproducible demo dataset.
WARNING: Re-running this script clears this project's collections before seeding.
"""
import os, sys, random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt

random.seed(42)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / "backend" / ".env")
uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
db_name = os.getenv("DATABASE_NAME", "food_delivery_analytics")
client = MongoClient(uri, serverSelectionTimeoutMS=10000)
client.admin.command("ping")
db = client[db_name]
COLLECTIONS = ["users", "orders", "customers", "restaurants", "menu_items", "deliveries", "reviews"]
for name in COLLECTIONS:
    db[name].delete_many({})
now = datetime.now(timezone.utc)
db.users.insert_one({"name":"FoodPulse Admin","email":"admin@foodpulse.com","password_hash":bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode(),"role":"admin","created_at":now})

cities = ["Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Chennai", "Pune", "Mysuru", "Kolkata", "Ahmedabad", "Jaipur"]
cuisines = ["South Indian", "North Indian", "Fast Food", "Italian", "Chinese", "Healthy", "Biryani", "Desserts", "Pizza", "Cafe"]
restaurant_names = ["Spice Route", "Burger Junction", "Green Bowl", "Pizza Corner", "Namma Meals", "Wok Express", "Biryani House", "Sweet Treats", "Urban Cafe", "Tandoori Tales"]
restaurants=[]
for i in range(100):
    restaurants.append({"name": f"{restaurant_names[i%len(restaurant_names)]} {i+1:03d}", "cuisine": random.choice(cuisines), "city": random.choice(cities), "rating": round(random.uniform(3.0,5.0),1), "is_active": random.random()>.08, "created_at": now-timedelta(days=random.randint(30,900))})
res = db.restaurants.insert_many(restaurants)
for r, oid in zip(restaurants, res.inserted_ids): r["id"] = str(oid)

first_names=["Aarav","Aditi","Akash","Ananya","Arjun","Diya","Ishaan","Kavya","Meera","Neha","Rahul","Riya","Sanjay","Sneha","Varun","Vikram","Priya","Kiran","Pooja","Manoj"]
customers=[]
for i in range(1200):
    customers.append({"name":f"{random.choice(first_names)} Customer {i+1:04d}","email":f"customer{i+1:04d}@example.com","phone":f"9{random.randint(100000000,999999999)}","city":random.choice(cities),"created_at":now-timedelta(days=random.randint(1,1000))})
cres=db.customers.insert_many(customers)
for c,oid in zip(customers,cres.inserted_ids): c["id"]=str(oid)

food_templates=[("Masala Dosa","Breakfast",90),("Idli Vada","Breakfast",70),("Classic Burger","Fast Food",160),("French Fries","Sides",90),("Paneer Salad Bowl","Healthy",210),("Margherita Pizza","Pizza",250),("Farmhouse Pizza","Pizza",320),("Mini Meals","Meals",140),("Veg Biryani","Biryani",220),("Hakka Noodles","Chinese",180),("Chocolate Brownie","Desserts",120),("Cold Coffee","Beverages",110),("Paneer Tikka","Starters",240),("Chicken Biryani","Biryani",280),("Gulab Jamun","Desserts",80)]
menu=[]
# Guarantee every restaurant has at least one menu item. Otherwise, a randomly
# selected restaurant may have no entry in menu_by_rest when orders are seeded.
for i, r in enumerate(restaurants):
    food, cat, price = random.choice(food_templates)
    menu.append({"restaurant_id":r["id"],"restaurant_name":r["name"],"name":f"{food} {i+1:03d}","category":cat,"price":round(price*random.uniform(.8,1.4),2),"is_available":random.random()>.07,"created_at":now-timedelta(days=random.randint(1,500))})
for i in range(len(restaurants), 350):
    r=random.choice(restaurants); food,cat,price=random.choice(food_templates)
    menu.append({"restaurant_id":r["id"],"restaurant_name":r["name"],"name":f"{food} {i+1:03d}","category":cat,"price":round(price*random.uniform(.8,1.4),2),"is_available":random.random()>.07,"created_at":now-timedelta(days=random.randint(1,500))})
mres=db.menu_items.insert_many(menu)
for m,oid in zip(menu,mres.inserted_ids): m["id"]=str(oid)
menu_by_rest={}
for m in menu: menu_by_rest.setdefault(m["restaurant_id"],[]).append(m)
statuses=["delivered","delivered","delivered","preparing","out_for_delivery","cancelled","confirmed","placed"]
payments=["UPI","Card","Cash","Wallet"]
orders=[]
for i in range(2500):
    r=random.choice(restaurants); c=random.choice(customers); item=random.choice(menu_by_rest[r["id"]]); qty=random.randint(1,4); status=random.choice(statuses)
    od=now-timedelta(days=random.randint(0,364),hours=random.randint(0,23),minutes=random.randint(0,59))
    delivery_minutes=random.randint(15,65) if status=="delivered" else None
    orders.append({"order_code":f"FP-{od:%y%m}-{i+1:06d}","customer_id":c["id"],"customer_name":c["name"],"customer_email":c["email"],"restaurant_id":r["id"],"restaurant_name":r["name"],"items":[{"name":item["name"],"quantity":qty,"price":item["price"],"category":item["category"]}],"total_amount":round(item["price"]*qty+random.choice([20,25,30,35]),2),"payment_method":random.choice(payments),"status":status,"city":r["city"],"delivery_minutes":delivery_minutes,"rating":round(random.uniform(3,5),1) if status=="delivered" else None,"device":random.choice(["Android","iOS","Web"]),"order_date":od,"created_at":od})
ores=db.orders.insert_many(orders)
# Deliveries refer to order IDs/codes and cover delivered/in-flight/cancelled outcomes.
deliveries=[]
partners=["Rider A","Rider B","Rider C","Rider D","Rider E","Rider F","Rider G","Rider H"]
for i,o in enumerate(orders):
    if o["status"] in ("cancelled","placed","confirmed","preparing"): dstatus="cancelled" if o["status"]=="cancelled" else "assigned"
    else: dstatus=random.choice(["delivered","delivered","delivered","in_transit"])
    deliveries.append({"order_id":o["order_code"],"order_code":o["order_code"],"customer_name":o["customer_name"],"restaurant_name":o["restaurant_name"],"city":o["city"],"partner_name":random.choice(partners),"status":dstatus,"delivery_minutes":o["delivery_minutes"] or (random.randint(20,60) if dstatus=="delivered" else None),"distance_km":round(random.uniform(.5,15),1),"delivery_date":o["order_date"],"created_at":o["order_date"]})
db.deliveries.insert_many(deliveries)
reviews=[]
for i in range(1800):
    o=random.choice(orders)
    reviews.append({"order_code":o["order_code"],"customer_name":o["customer_name"],"restaurant_name":o["restaurant_name"],"city":o["city"],"rating":round(random.uniform(1,5),1),"review_text":random.choice(["Great food","Delivered on time","Could be better","Excellent service","Food was fresh","Delivery was delayed"]),"created_at":o["order_date"]})
db.reviews.insert_many(reviews)
for coll, fields in [("orders",["order_date","status","restaurant_id","customer_id"]),("deliveries",["delivery_date","status","city"]),("menu_items",["category","restaurant_id"]),("customers",["city"]),("restaurants",["city","cuisine"])]:
    for field in fields: db[coll].create_index(field)
print(f"Seed complete: {db_name}")
print("Demo login: admin@foodpulse.com / Admin@123")
for name in COLLECTIONS: print(f"{name}: {db[name].count_documents({}):,} records")
