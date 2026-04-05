from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import hmac
import hashlib
import json
import os

# ---- Configuration ----
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

LEMON_API_KEY = os.getenv("LEMON_API_KEY", "") 
LEMON_WEBHOOK_SECRET = os.getenv("LEMON_WEBHOOK_SECRET", "my_lemon_secret")
ADMIN_USER = os.getenv("ADMIN_USER")  # Configure these exclusively in Render Environment Variables
ADMIN_PASS = os.getenv("ADMIN_PASS")

# ---- Database Setup ----
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "profiles_v2"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # (In production, use Passlib to hash)
    lemon_customer_id = Column(String, unique=True, index=True, nullable=True)
    subscription_status = Column(String, default="inactive") # 'active' or 'inactive'

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database connection warning: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- FastAPI App ----
app = FastAPI(title="ShortsStudio Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ShortsStudio API is fully operational"}

@app.post("/auth/login")
def login(user_data: dict, db: Session = Depends(get_db)):
    """Simple placeholder login. Checks plaintext password."""
    username = user_data.get("username")
    password = user_data.get("password")
    
    # ---- Admin Bypass ----
    if ADMIN_USER and ADMIN_PASS and username == ADMIN_USER and password == ADMIN_PASS:
        return {
            "user_id": 999999,
            "username": "swappy",
            "subscription_status": "active"
        }
    # ----------------------
    
    user = db.query(UserProfile).filter(UserProfile.username == username).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "subscription_status": user.subscription_status
    }

@app.post("/auth/register")
def register(user_data: dict, db: Session = Depends(get_db)):
    """Register a new user. Default status is inactive."""
    username = user_data.get("username")
    password = user_data.get("password")
    
    if db.query(UserProfile).filter(UserProfile.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
        
    new_user = UserProfile(username=username, password_hash=password, subscription_status="inactive")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created", "user_id": new_user.id}

@app.get("/user/{user_id}/status")
def check_status(user_id: int, db: Session = Depends(get_db)):
    """The Desktop executable polls this to see if the user is allowed to use the app."""
    if user_id == 999999: # Admin bypass ID
        return {"subscription_status": "active"}
        
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"subscription_status": user.subscription_status}

@app.post("/lemonsqueezy/webhook")
async def lemonsqueezy_webhook(request: Request, db: Session = Depends(get_db)):
    """Listens for successful Lemon Squeezy subscriptions and updates the Database."""
    payload = await request.body()
    signature = request.headers.get("x-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature header")

    # Verify signature
    secret = LEMON_WEBHOOK_SECRET.encode('utf-8')
    computed_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(computed_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse Event
    data = await request.json()
    event_name = data['meta']['event_name']
    custom_data = data['meta'].get('custom_data', {})
    
    # We will pass the 'username' or 'user_id' in the checkout link custom data 
    # so Lemon Squeezy sends it back to us here!
    checkout_username = custom_data.get('username')

    if event_name in ['subscription_created', 'subscription_updated']:
        status = data['data']['attributes']['status']
        customer_id = str(data['data']['attributes']['customer_id'])
        
        # Internal status rules
        internal_status = 'active' if status in ['active', 'trialing', 'past_due'] else 'inactive'
        
        # Find user by internal username we tracked during checkout
        if checkout_username:
            user = db.query(UserProfile).filter(UserProfile.username == checkout_username).first()
            if user:
                user.subscription_status = internal_status
                user.lemon_customer_id = customer_id
                db.commit()
                print(f"✅ Updated user {user.username} to {internal_status}")

    elif event_name in ['subscription_cancelled', 'subscription_expired']:
        customer_id = str(data['data']['attributes']['customer_id'])
        
        user = db.query(UserProfile).filter(UserProfile.lemon_customer_id == customer_id).first()
        if user:
            user.subscription_status = 'inactive'
            db.commit()
            print(f"❌ Revoked access for Lemon Squeezy customer {customer_id}")

    return {"status": "success"}
