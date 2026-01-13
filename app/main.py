import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import User
from .schemas import UserCreate, UserOut
from .utils import get_password_hash

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Auth Lab 1"),
    description="User registration with secure password hashing",
    version="1.0.0"
)


# Dependency: Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Health check endpoint
@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}


# User registration endpoint
@app.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash the password (NEVER store plain text!)
    hashed_password = get_password_hash(payload.password)

    # Create new user instance
    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
        is_active=True
    )

    try:
        # Add to session and commit to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)  # Reload from DB to get the ID

        return new_user

    except IntegrityError:
        # Rollback in case of database constraint violation
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )