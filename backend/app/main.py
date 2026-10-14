from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.db.mongodb import check_connection, create_indexes
from app.routes import auth, orders, resources, analytics, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_connection()
    create_indexes()
    yield

app = FastAPI(title="FoodPulse Analytics API", version="1.0.0", description="Online food delivery operations and analytics API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(resources.router)
app.include_router(analytics.router)
app.include_router(reports.router)

@app.get("/")
def root():
    return {"message": "FoodPulse Analytics API is running", "docs": "/docs"}

@app.get("/health")
def health():
    check_connection()
    return {"status": "ok", "database": "connected"}
