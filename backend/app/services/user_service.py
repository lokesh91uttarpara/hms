from app.db import get_connection
from app.core.auth_utils import verify_password

def authenticate_user(user_id: str, password: str,user_type:str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM md_user WHERE user_id = %s AND user_type =%s " , (user_id,user_type))
            user = cursor.fetchone()
            if user and verify_password(password, user["pass"]):
                return {"user_id": user["user_id"]}
            return None
    finally:
        conn.close()
