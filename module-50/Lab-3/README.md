# Lab 3 – Session Lifecycle & Refresh Tokens

Welcome to Lab 3! In the previous labs, you built a complete authentication system with user registration and JWT-based login. But there's a critical problem we haven't addressed yet: access tokens expire quickly (30 minutes), forcing users to log in repeatedly. In this lab, you'll implement a production-ready solution using refresh tokens that balance security with user convenience.

## Objectives

- Understand the security tradeoffs of token expiration
- Implement dual-token architecture (short-lived access + long-lived refresh)
- Create refresh token storage in the database
- Build `/refresh` endpoint to issue new access tokens
- Handle token expiration errors gracefully
- Test the complete token lifecycle with expiration scenarios

## Background

### The Token Expiration Problem

In Lab 2, we set access tokens to expire after 30 minutes. This is good security - if someone steals a token, they can only use it for 30 minutes. But it creates a terrible user experience. Imagine you're writing a long email in a web app and after 30 minutes, boom - you're logged out and might lose your work.

The naive solution would be to make tokens last longer, maybe 7 days or even 30 days. But now if someone steals your token, they have access for a whole month. That's unacceptable for sensitive applications. We need something better.

### Enter Refresh Tokens

The solution is to use **two types of tokens** with different purposes and lifespans:

**Access Token** - This is what you've been using in Lab 2. It's short-lived (15 minutes in production) and included in every API request. If it's stolen, the damage is limited because it expires quickly. This token is never stored anywhere - the client keeps it in memory.

**Refresh Token** - This is a long-lived token (7 days or more) with one specific purpose: getting new access tokens. The client stores this securely and only sends it to one endpoint: `/refresh`. When the access token expires, instead of asking for the password again, the client sends the refresh token to get a new access token. The user stays logged in seamlessly.

Think of it like a hotel key card system. Your room key (access token) expires every evening for security. But you don't need to go through the full check-in process again - you just go to the lobby kiosk with your ID bracelet (refresh token) and get a new room key instantly.

### How Dual-Token Architecture Works

Here's the complete authentication flow with refresh tokens:

**Initial Login:**
1. User sends email and password to `POST /login`
2. Server verifies credentials
3. Server creates **both** an access token (15 min) and refresh token (7 days)
4. Server stores refresh token in database with user ID and expiration
5. Server returns both tokens to client
6. Client stores access token in memory, refresh token in secure storage

**Accessing Protected Resources:**
1. Client sends access token in Authorization header
2. Server validates token signature and expiration
3. If valid, server grants access
4. If expired, server returns 401 with "token expired" error
5. Client automatically calls `/refresh` endpoint

**Refreshing Access Token:**
1. Client sends refresh token to `POST /refresh`
2. Server validates refresh token signature
3. Server checks if refresh token exists in database and hasn't expired
4. If valid, server issues a new access token (15 min)
5. Server optionally issues a new refresh token (token rotation)
6. Client stores new tokens and retries the original request

**Logout:**
1. Client calls `POST /logout` with refresh token
2. Server deletes refresh token from database
3. Client deletes both tokens from storage
4. Old access token still works until it expires, but can't get new ones

### Why Store Refresh Tokens in the Database?

You might wonder why we store refresh tokens in the database when the whole point of JWT was to avoid server-side storage. The answer is control.

With access tokens, we accept that once issued, they work until expiration. Fifteen minutes is short enough that we can live with that risk. But refresh tokens last 7 days. If a user's device is compromised, we need the ability to revoke their refresh token immediately.

By storing refresh tokens in the database, we can:
- **Revoke specific tokens** - If a user reports a stolen device, delete that device's refresh token
- **Revoke all tokens** - If an account is compromised, delete all refresh tokens, forcing re-login
- **Track devices** - See which devices/browsers a user is logged in on
- **Implement security policies** - Limit number of active sessions, detect suspicious activity

The database check only happens during refresh (maybe once per hour), not on every request. The access token remains stateless for performance.

### Token Rotation Strategy

There are two approaches to refresh tokens:

**Non-Rotating Refresh Tokens** - The refresh token stays the same until it expires. Simpler to implement, but if the token is stolen, the attacker can use it for days.

**Rotating Refresh Tokens** - Every time you refresh, you get a new refresh token and the old one is invalidated. If a token is used twice, it indicates theft, and all tokens for that user can be revoked. More secure, but adds complexity.

In this lab, we'll implement non-rotating tokens for simplicity. In a production system, you'd want rotation.

### Security Considerations

**Refresh Token Storage on Client** - Never store refresh tokens in localStorage - JavaScript can access it, making it vulnerable to XSS attacks. Store in httpOnly cookies (server sets them, JS can't read them) or in secure mobile storage (iOS Keychain, Android Keystore).

**Refresh Token Transmission** - Only send refresh tokens over HTTPS. Unlike access tokens that are sent frequently, refresh tokens are sent rarely but are more valuable.

**Refresh Token Entropy** - Refresh tokens should be long and random (at least 32 bytes of entropy). While we're using JWT for simplicity, production systems often use random strings for refresh tokens.

**One-Time Refresh Tokens** - Some systems implement single-use refresh tokens. Each refresh invalidates the old token and issues a new one. If an old token is reused, it indicates theft.

**Refresh Token Expiration** - Seven days is common for web apps. Mobile apps might use 30 days or even 90 days since the device is presumably more secure. Banking apps might use shorter periods.

### Database Schema Changes

We need to store refresh tokens, so we'll add a new table:

```
refresh_tokens table:
┌────┬─────────┬─────────────────────┬────────────────────┬──────────────────┐
│ id │ user_id │ token               │ expires_at         │ created_at       │
├────┼─────────┼─────────────────────┼────────────────────┼──────────────────┤
│ 1  │ 1       │ eyJhbGciOiJIUzI1... │ 2024-01-24 10:00   │ 2024-01-17 10:00 │
│ 2  │ 1       │ eyJhbGciOiJIUzI1... │ 2024-01-25 14:30   │ 2024-01-18 14:30 │
│ 3  │ 2       │ eyJhbGciOiJIUzI1... │ 2024-01-23 08:15   │ 2024-01-16 08:15 │
└────┴─────────┴─────────────────────┴────────────────────┴──────────────────┘
```

Each user can have multiple refresh tokens (one per device/browser). When they refresh, we check if the token exists in this table and hasn't expired.

## Prerequisites

**IMPORTANT:** Lab 3 will be done on a fresh Poridhi VM (different from Labs 1 and 2). This means your database will be empty and you'll start with a clean environment.

This lab builds on the code from Lab 2. You have two options:

**Option 1: Clone the Lab 2 code from GitHub (Recommended)**

```bash
git clone https://github.com/poridhioss/Building-Systems-With-FastAPI.git
cd Building-Systems-With-FastAPI/
git checkout -b mod-50/lab-2 origin/mod-50/lab-2
```

**Option 2: Use your own Lab 2 implementation**

If you completed Lab 2 and pushed your code to GitHub, you can clone your own repository.

Either way, you'll need:
- Lab 2 code with working login and JWT authentication
- PostgreSQL database setup (we'll start it fresh in this lab)
- Virtual environment ready to install dependencies

Check `python --version` in the bash terminal. If it doesn't work, run:
```bash
sudo apt update
sudo apt install python3.12-venv -y
alias python=python3.12
source ~/.bashrc
```

## Project Structure

We'll add new files and modify existing ones:

```
Root directory
    ├── docker-compose.yml
    ├── .env                        # Update token expiration times
    ├── .env.example
    ├── requirements.txt            # No new dependencies needed
    ├── alembic.ini
    ├── .gitignore
    │
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # Add /refresh and /logout endpoints
    │   ├── database.py
    │   ├── models.py               # Add RefreshToken model
    │   ├── schemas.py              # Add RefreshTokenRequest schema
    │   ├── utils.py
    │   ├── auth.py                 # Add refresh token functions
    │   └── config.py               # Update with refresh token settings
    │
    └── alembic/
        └── versions/
            └── xxxx_add_refresh_tokens_table.py  # New migration
```

## Step-by-Step Implementation Guide

### Step 1: Update Configuration

First, let's update our environment variables to include refresh token settings. Update your `.env` file. Here's the COMPLETE `.env` file:

```env
# ========== FROM LAB 1 ==========
APP_NAME=FastAPI Auth Lab 3
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db

# ========== FROM LAB 2 ==========
JWT_SECRET=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256

# ========== UPDATED IN LAB 3 ==========
ACCESS_TOKEN_EXPIRE_MINUTES=15

# ========== NEW IN LAB 3 ==========
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Also update `.env.example`. Here's the COMPLETE `.env.example` file:

```env
# ========== FROM LAB 1 ==========
APP_NAME=FastAPI Auth Lab 3
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db

# ========== FROM LAB 2 ==========
JWT_SECRET=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256

# ========== UPDATED IN LAB 3 ==========
ACCESS_TOKEN_EXPIRE_MINUTES=15

# ========== NEW IN LAB 3 ==========
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Notice we've reduced the access token lifetime from 30 minutes to 15 minutes. This is more secure, and users won't notice because the refresh mechanism keeps them logged in.

### Step 2: Update Config Module

Update `app/config.py` to include the new refresh token settings. Here's the COMPLETE `app/config.py` file:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ========== FROM LAB 2 ==========
    APP_NAME: str = os.getenv("APP_NAME", "FastAPI Auth Lab 3")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # ========== UPDATED IN LAB 3 ==========
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # ========== NEW IN LAB 3 ==========
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


settings = Settings()
```

### Step 3: Add RefreshToken Model

Now we need to add a database model to store refresh tokens. Update `app/models.py`. Here's the COMPLETE `app/models.py` file:

```python
# ========== FROM LAB 1 ==========
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# ========== NEW IN LAB 3 ==========
from sqlalchemy import ForeignKey

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("token", name="uq_refresh_tokens_token"),
    )

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
```

The `RefreshToken` model stores each refresh token with its expiration time and which user it belongs to. The `ForeignKey` with `ondelete="CASCADE"` means if a user is deleted, all their refresh tokens are automatically deleted too.

### Step 4: Start PostgreSQL Database

Since this is a fresh VM, we need to start PostgreSQL first before we can create migrations:

```bash
# Start PostgreSQL in the background
docker compose up -d
```

Wait for it to be ready:

```bash
# Check if container is running and healthy
docker compose ps
```

![alt text](./images/image-6.png)

You should see the database container running with a "healthy" status.

### Step 5: Create Virtual Environment and Install Dependencies

Now create the virtual environment and install all required packages:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

### Step 6: Create Database Migration

You need to apply all existing migrations before creating a new one:

# First, apply all existing migrations

```bash
alembic upgrade head
```

This will run all the migrations from Labs 1 and 2 (creating the users table, etc.).

Then you can create the new migration:

Now that the database is running and dependencies are installed, create a new migration for the refresh_tokens table:

```bash
# Generate migration
alembic revision --autogenerate -m "Add refresh_tokens table"
```

You should see output indicating a new migration file was created in `alembic/versions/`.

Apply the migration:

```bash
alembic upgrade head
```

Verify the tables were created:

```bash
docker compose exec db psql -U postgres -d auth_lab1_db -c "\dt"
```

You should see both the `users` and `refresh_tokens` tables.

### Step 7: Update Schemas

Add schemas for refresh token operations. Update `app/schemas.py`. Here's the COMPLETE `app/schemas.py` file:

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ========== FROM LAB 1 ==========
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True


# ========== FROM LAB 2 ==========
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ========== UPDATED IN LAB 3 ==========
class Token(BaseModel):
    access_token: str
    refresh_token: str  # NEW: now includes refresh token
    token_type: str


# ========== NEW IN LAB 3 ==========
class RefreshTokenRequest(BaseModel):
    refresh_token: str
```

Notice the `Token` schema now includes a `refresh_token` field. When users log in, they'll receive both tokens.

### Step 8: Update Authentication Module

Now we need to add functions for creating and validating refresh tokens. Update `app/auth.py`. Here's the COMPLETE `app/auth.py` file:

```python
# ========== FROM LAB 2 ==========
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import User
from .schemas import TokenData

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

        token_data = TokenData(email=email)
        return token_data

    except JWTError:
        raise credentials_exception


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = verify_token(token, credentials_exception)

    user = db.query(User).filter(User.email == token_data.email).first()

    if user is None:
        raise credentials_exception

    return user


# ========== NEW IN LAB 3 ==========
from .models import RefreshToken
from datetime import timezone

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt, expire


def verify_refresh_token(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if email is None or token_type != "refresh":
            raise credentials_exception

        # Check if refresh token exists in database and hasn't been revoked
        db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()

        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        # Check if token is expired (database-level check)
        if db_token.expires_at < datetime.now(timezone.utc):
            db.delete(db_token)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        return email

    except JWTError:
        raise credentials_exception


def store_refresh_token(db: Session, user_id: int, token: str, expires_at: datetime):
    db_refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    return db_refresh_token


def revoke_refresh_token(db: Session, token: str):
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False


def revoke_all_user_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
    db.commit()
```

Let's break down the new functions:

**create_refresh_token()** - Similar to `create_access_token()` but with a longer expiration (7 days). It also adds a "type": "refresh" claim so we can distinguish refresh tokens from access tokens. It returns both the token and the expiration datetime (we need to store the expiration in the database).

**verify_refresh_token()** - This validates a refresh token. First, it decodes the JWT and verifies the signature. Then it checks if the token type is "refresh" (not "access"). Most importantly, it checks if the token exists in the database - if someone logs out, their refresh token is deleted, so even if the JWT signature is valid, we reject it. Finally, it checks if the token has expired in the database.

**store_refresh_token()** - Saves a refresh token to the database after login. This is how we track active sessions.

**revoke_refresh_token()** - Deletes a specific refresh token from the database. Used for logout.

**revoke_all_user_tokens()** - Deletes all refresh tokens for a user. Useful for "log out all devices" functionality or when a user changes their password.

### Step 9: Update Main Application

Now let's update the main application to issue both tokens on login and add the refresh and logout endpoints. Update `app/main.py`. Here's the COMPLETE `app/main.py` file:

```python
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
```

Let's examine the new and updated endpoints:

**POST /login (updated)** - Now creates both access and refresh tokens. The refresh token is stored in the database with its expiration time. The response includes both tokens.

**POST /refresh (new)** - Takes a refresh token, validates it (checks signature, database existence, expiration), and issues a new access token. The refresh token stays the same. In production systems, you might want to rotate the refresh token here too (issue a new one and delete the old one).

**POST /logout (new)** - Takes a refresh token and deletes it from the database. After this, that refresh token can't be used anymore, even though it's still a valid JWT. The old access token will continue to work until it expires (15 minutes), but the user can't get a new one.

**POST /logout-all (new)** - This is a protected endpoint (requires access token) that deletes all refresh tokens for the current user. Useful for "log out everywhere" functionality, like when you change your password or suspect your account was compromised.

### Step 10: Run Your FastAPI Application

Start the application:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 11: Set Up Poridhi Load Balancer

Find your wt0 IP address:

```bash
ifconfig
```

![alt text](./images/image.png)

Look for the wt0 interface and note the IP address (something like `100.125.xxx.xxx`).

Go to Poridhi's Load Balancer dashboard, create a new Load Balancer using your wt0 IP with port 8000. You'll get a public URL like `https://lb-xxxxx.poridhi.io`.

![alt text](./images/image-1.png)

### Step 12: Test the Complete Token Lifecycle

Open Swagger UI at `<Load Balancer URL>/docs`.

![alt text](./images/image-2.png)

**Step 12.1: Register a test user**

Since this is a fresh VM with an empty database, register a user first. Click `POST /register`, then "Try it out":

```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

You should get a 201 response with the user details.

**Step 12.2: Login and receive both tokens**

Click `POST /login`, then "Try it out":

```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

You should get a response like:

![alt text](./images/image-3.png)

Copy both tokens. The access token is much shorter (expires in 15 minutes), the refresh token is for 7 days.

**Step 12.3: Access protected route with access token**

Click the "Authorize" button at the top right of Swagger UI. Paste your **access token** (not the refresh token) into the field. Click "Authorize" then "Close".

![alt text](./images/image-4.png)

Now execute `GET /users/me`. You should see your user information.

![alt text](./images/image-5.png)

**Step 12.4: Test the refresh endpoint**

Click `POST /refresh`, then "Try it out". In the request body, paste your **refresh token**:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

You should get a new access token:

![alt text](./images/image-7.png)

The refresh token is the same, but you have a brand new access token that's valid for another 15 minutes.

**Step 12.5: Test logout**

Click `POST /logout`, then "Try it out". Paste your refresh token:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

You should get:

![alt text](./images/image-8.png)

Now try using the `/refresh` endpoint with that same refresh token again. You should get a 401 error saying "Refresh token has been revoked".

![alt text](./images/image-9.png)

Your access token still works (try `GET /users/me`) until it expires, but you can't get a new one.

![alt text](./images/image-10.png)

**Step 12.6: Test logout from all devices**

First, login again to get new tokens. Then click the "Authorize" button and paste your new access token.

Execute `POST /logout-all`. You should get:

```json
{
  "message": "Successfully logged out from all devices"
}
```

This deletes all refresh tokens for your user from the database. If you were logged in on multiple devices, none of them could refresh their access tokens anymore.

### Step 13: Test with curl

You can also test the complete flow with curl:

**Register:**
```bash
curl -X POST "<Load Balancer URL>/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "BobPassword456!"
  }'
```

**Login and save tokens:**
```bash
response=$(curl -X POST "<Load Balancer URL>/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "BobPassword456!"
  }')

echo $response

# Extract tokens (you'll need jq for this)
access_token=$(echo $response | jq -r '.access_token')
refresh_token=$(echo $response | jq -r '.refresh_token')

echo "Access Token: $access_token"
echo "Refresh Token: $refresh_token"
```

**Access protected route:**
```bash
curl -X GET "<Load Balancer URL>/users/me" \
  -H "Authorization: Bearer $access_token"
```

**Refresh access token:**
```bash
new_response=$(curl -X POST "<Load Balancer URL>/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$refresh_token\"}")

echo $new_response

new_access_token=$(echo $new_response | jq -r '.access_token')
echo "New Access Token: $new_access_token"
```

**Logout:**
```bash
curl -X POST "<Load Balancer URL>/logout" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$refresh_token\"}"
```

**Try to refresh after logout (should fail):**
```bash
curl -X POST "<Load Balancer URL>/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$refresh_token\"}"
```

You'll get a 401 error saying the refresh token has been revoked.


Notice that each login creates a new refresh token. If a user logs in from multiple devices (or multiple browsers), they'll have multiple refresh tokens. Each one works independently.

### Step 14: Understanding the Security Model

Let's review what we've built and why it's secure:

**Short-lived access tokens** - Expire in 15 minutes. If stolen, an attacker only has 15 minutes to use it. They can't get a new one without the refresh token.

**Long-lived refresh tokens** - Last 7 days but are only sent to one endpoint (`/refresh`), reducing exposure. Stored in the database so they can be revoked.

**Database-backed revocation** - Even if a refresh token's JWT signature is valid and it hasn't expired, if it's not in the database, it doesn't work. This gives you instant revocation capability.

**Logout everywhere** - Users can revoke all their refresh tokens at once, logging out all devices. Useful after a password change or security incident.

**Separate token types** - Refresh tokens have "type": "refresh" in their payload. Access tokens don't. This prevents using a refresh token as an access token or vice versa.

**No password in tokens** - Neither token type contains the password, obviously. But more subtly, they only contain the email. Even if someone decodes the token, they don't learn anything they didn't already know.

**HTTPS required** - In production, all of this only works over HTTPS. Without encryption, tokens can be intercepted in transit.

## Conclusion

Congratulations! You've built a production-ready authentication system with dual-token architecture. Your users can stay logged in for days without compromising security because the tokens they use for API requests expire quickly. The refresh token mechanism provides a seamless experience - users don't even know their access token is being refreshed in the background.

You've learned about the tradeoffs between security and convenience, and how refresh tokens let you have both. You understand how to store refresh tokens in the database to enable revocation, a critical security feature. You've also implemented logout functionality that actually works - the user can't keep using the API after logout because their refresh token is gone.

The authentication system you've built in these three labs forms the foundation of most modern web applications. From social media to banking apps, the patterns you've learned - password hashing, JWT access tokens, and refresh tokens - are used everywhere. You're now equipped to build secure, scalable authentication systems for real-world applications.
