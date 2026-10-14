import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://rajeshrajini1523_db_user:< Zk898OjR0po9nWsq>@foodpulsecluster.tds0cfo.mongodb.net/?appName=FoodPulseCluster")
DATABASE_NAME = os.getenv("DATABASE_NAME", "food_delivery_analytics")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-to-a-long-random-secret")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
