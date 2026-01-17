# ========== IMPORTS FROM LAB 1 ==========
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import User
from .schemas import UserCreate, UserOut
from .utils import get_password_hash

# ========== IMPORTS FROM LAB 2 ==========
from datetime import timedelta
from .schemas import UserLogin, Token
from .utils import verify_password
from .auth import create_access_token, get_current_user
from .config import settings

# ========== NEW IMPORTS IN LAB 3 ==========
from .schemas import RefreshTokenRequest
from .auth import (
    create_refresh_token,
    verify_refresh_token,
    store_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens
)

# ========== FROM LAB 1 ==========
load_dotenv()

app = FastAPI(
    title=settings.APP_NAME,
    description="User authentication with JWT and refresh tokens",  # UPDATED in Lab 3
    version="3.0.0"  # UPDATED in Lab 3
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}


@app.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(payload.password)

    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
        is_active=True
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )


# ========== UPDATED IN LAB 3 ==========
@app.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    # FROM LAB 2: Find user and verify credentials
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # FROM LAB 2: Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    # NEW IN LAB 3: Create refresh token
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token, refresh_expires_at = create_refresh_token(
        data={"sub": user.email},
        expires_delta=refresh_token_expires
    )

    # NEW IN LAB 3: Store refresh token in database
    store_refresh_token(db, user.id, refresh_token, refresh_expires_at)

    # UPDATED IN LAB 3: Return both tokens
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ========== FROM LAB 2 ==========
@app.get("/users/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


# ========== NEW IN LAB 3 ==========
@app.post("/refresh", response_model=Token)
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Verify the refresh token
    email = verify_refresh_token(payload.refresh_token, db)

    # Get user from database
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    # Return new access token with the same refresh token
    # In production, you might want to rotate the refresh token here
    return {
        "access_token": access_token,
        "refresh_token": payload.refresh_token,
        "token_type": "bearer"
    }


@app.post("/logout")
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Revoke the refresh token
    revoked = revoke_refresh_token(db, payload.refresh_token)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found"
        )

    return {"message": "Successfully logged out"}


@app.post("/logout-all")
def logout_all_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Revoke all refresh tokens for the current user
    revoke_all_user_tokens(db, current_user.id)

    return {"message": "Successfully logged out from all devices"}