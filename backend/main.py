from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import stripe
import os

# ---- Configuration ----
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")

stripe.api_key = STRIPE_SECRET_KEY

# ---- Database Setup ----
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)  # (In production, use Passlib to hash)
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    subscription_status = Column(String, default="inactive") # 'active' or 'inactive'

Base.metadata.create_all(bind=engine)

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
    # TODO: Implement secure password hashing, JWTs, and real session tokens.
    username = user_data.get("username")
    password = user_data.get("password")
    
    user = db.query(UserProfile).filter(UserProfile.username == username).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "subscription_status": user.subscription_status
    }

@app.get("/user/{user_id}/status")
def check_status(user_id: int, db: Session = Depends(get_db)):
    """The Desktop executable polls this to see if the user is allowed to use the app."""
    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"subscription_status": user.subscription_status}

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Listens for successful Stripe subscriptions and updates the Database."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle the event
    if event['type'] == 'customer.subscription.created' or event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        # Determine internal status
        internal_status = 'active' if status in ['active', 'trialing'] else 'inactive'
        
        # Find user by Stripe customer ID and authorize them
        user = db.query(UserProfile).filter(UserProfile.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = internal_status
            db.commit()
            print(f"✅ Updated user {user.username} to {internal_status}")

    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        
        user = db.query(UserProfile).filter(UserProfile.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = 'inactive'
            db.commit()
            print(f"❌ Revoked access for user {user.username}")

    return {"status": "success"}
