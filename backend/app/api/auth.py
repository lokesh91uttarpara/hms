from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.user_service import authenticate_user
from app.core.auth_utils import create_access_token

router = APIRouter()
class LoginRequest(BaseModel):
    user_id: str
    pass_: str  # underscore to avoid keyword conflict
    user_type : str

@router.post("/login")
def login(form: LoginRequest):
    user_id = form.user_id
    password = form.pass_
    user_type = form.user_type
    
    user = authenticate_user(user_id,password,user_type)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["user_id"]})
    return {"access_token": token, "token_type": "bearer","user_id" : user_id,"user_type" : user_type }
