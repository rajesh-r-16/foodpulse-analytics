from fastapi import APIRouter, HTTPException, Depends
from app.schemas import LoginInput
from app.db.mongodb import db
from app.core.security import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login")
def login(payload: LoginInput):
    user = db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {
        "access_token": create_access_token(user["email"]),
        "token_type": "bearer",
        "user": {"name": user.get("name", "Admin"), "email": user["email"], "role": user.get("role", "admin")}
    }

@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
