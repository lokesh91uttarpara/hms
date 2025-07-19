from fastapi import FastAPI
from app.api import auth, bookings, guests,master
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://frontend-ip:port"]
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router, prefix="/auth")
app.include_router(bookings.router, prefix="/bookings")
app.include_router(guests.router, prefix="/guests")
app.include_router(master.router, prefix="/master")

# ✅ Add this at the end for testing password hash
if __name__ == "__main__":
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    plain = input("Enter password to hash: ")
    print("\nHashed password:")
    print(pwd.hash(plain))
