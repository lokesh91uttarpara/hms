from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db import get_connection
from app.services.booking_service import get_all_bookings
from app.core.auth_utils import verify_token

router = APIRouter()

security = HTTPBearer()

@router.get("/")
def list_bookings(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = verify_token(token)

    conn = get_connection()
    try:
        return "Ok Booking Api is working"
    finally:
        conn.close()
