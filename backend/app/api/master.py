from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db import get_connection
from app.core.auth_utils import verify_token
from pydantic import BaseModel

router = APIRouter()

security = HTTPBearer()
class add_room(BaseModel):
    room_no: str
    room_size: str
    room_type: str
@router.post("/add-room")
def add_room(
    room: add_room,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_data = verify_token(token)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO md_room (room_no, room_size, room_type)
                VALUES (%s, %s, %s)
            """
            values = (room.room_no,  room.room_size, room.room_type)
            cursor.execute(query, values)
            conn.commit()
        return {"status":"1","message": "Room added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
@router.get("/list-room")
def list_room(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_data = verify_token(token)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM md_room"
            cursor.execute(query)
            rooms = cursor.fetchall()  # Fetch all records

        return {"status": "1", "data": rooms, "message": "Rooms listed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
class EditRoom(BaseModel):
    room_id: int
    room_no: str
    room_size: str
    room_type: str

@router.post("/edit-room")
def edit_room(
    room: EditRoom,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_data = verify_token(token)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                UPDATE md_room
                SET room_size = %s, room_type = %s, room_no = %s
                WHERE id = %s
            """
            values = (room.room_size, room.room_type, room.room_no, room.room_id)
            cursor.execute(query, values)
            conn.commit()
        
        return {"status": "1", "message": "Room updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
       
