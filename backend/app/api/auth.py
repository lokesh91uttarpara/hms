from fastapi import APIRouter, HTTPException
from app.services.user_service import authenticate_user
from app.core.auth_utils import create_access_token

router = APIRouter()

@router.post("/login")
def login(form: dict):
    user_id = form.get("user_id")
    password = form.get("pass")
    
    user = authenticate_user(user_id, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["user_id"]})
    return {"access_token": token, "token_type": "bearer"}
