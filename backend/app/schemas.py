from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Literal
from datetime import datetime

class LoginInput(BaseModel):
    email: str
    password: str

class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    customer_email: Optional[str] = None
    restaurant_id: str
    restaurant_name: str
    items: list[dict] = []
    total_amount: float = Field(gt=0)
    payment_method: str = "UPI"
    status: Literal["placed", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"] = "placed"
    city: str = "Bengaluru"
    delivery_minutes: Optional[int] = None
    rating: Optional[float] = Field(default=None, ge=1, le=5)

class OrderUpdate(BaseModel):
    status: Optional[Literal["placed", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled"]] = None
    delivery_minutes: Optional[int] = None
    rating: Optional[float] = Field(default=None, ge=1, le=5)

class RestaurantCreate(BaseModel):
    name: str
    cuisine: str
    city: str = "Bengaluru"
    rating: float = Field(default=4.0, ge=0, le=5)
    is_active: bool = True

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: str = "Bengaluru"

class MenuItemCreate(BaseModel):
    restaurant_id: str
    restaurant_name: str
    name: str
    category: str
    price: float = Field(gt=0)
    is_available: bool = True

class DeliveryCreate(BaseModel):
    order_id: str
    partner_name: str
    status: str = "assigned"
    delivery_minutes: Optional[int] = None

class ReviewCreate(BaseModel):
    order_id: str
    restaurant_id: str
    restaurant_name: str
    customer_name: str
    rating: float = Field(ge=1, le=5)
    comment: str = ""
