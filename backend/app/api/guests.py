from fastapi import APIRouter
from app.db import get_connection
from app.services.booking_service import get_all_bookings

router = APIRouter()

@router.get("/")
def list_bookings():
    conn = get_connection()
    try:
        return get_all_bookings(conn)
    finally:
        conn.close()
