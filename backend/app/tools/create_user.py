import os
import pymysql
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash the password
password_plain = "1234"
hashed_password = pwd_context.hash(password_plain)

connection = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    db=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT")),
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        sql = "INSERT INTO md_user (user_id, pass) VALUES (%s, %s)"
        cursor.execute(sql, ("lokesh", hashed_password))
    connection.commit()
    print("User created successfully with hashed password.")
finally:
    connection.close()
