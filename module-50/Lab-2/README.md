# Lab 2 – The Authentication Core (Login & JWT Protection)

Welcome to Lab 2! In the previous lab, you built a solid foundation by implementing secure user registration with password hashing. Now it's time to bring your authentication system to life. In this lab, you'll implement the login mechanism that issues JWT tokens and create protected routes that require authentication. This is where users can actually prove who they are and access secured resources.

![Lab-2_high-level](https://raw.githubusercontent.com/poridhiEng/poridhi-labs/main/Poridhi%20Labs/Building%20Systems%20With%20FastAPI/module-50/lab-2/images/lab2-architecture.svg)

## Objectives

- Implement password verification against stored bcrypt hashes
- Understand JWT structure (Header, Payload, Signature)
- Create JWT access tokens using HS256 algorithm
- Build login endpoint that returns JWT tokens
- Implement authentication middleware (get_current_user dependency)
- Create protected routes that require valid tokens
- Test the complete authentication flow

## Background

### What is JWT (JSON Web Token)?

JWT is an open standard for securely transmitting information between parties as a JSON object. Think of it like a digital passport - just as a passport proves your identity when crossing borders, a JWT proves your identity when accessing protected API endpoints.

The beauty of JWT is that it's stateless. Unlike traditional session-based authentication where the server must remember who you are (by storing session data), JWT embeds all the necessary information inside the token itself. The server doesn't need to store anything - it just needs to verify the token's signature to confirm it's authentic and hasn't been tampered with.

When a user logs in successfully, the server creates a JWT and sends it to the client. From that point on, every time the client wants to access a protected resource, it includes this token in the request. The server validates the token and, if it's legitimate, grants access. No database lookups, no session storage - just cryptographic verification.

### JWT Structure

A JWT consists of three parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSIsImV4cCI6MTY3MDAwMDAwMH0.Kq1X8JJ5vY8pN2Q3R4S5T6U7V8W9X0Y1Z2A3B4C5D6E
     ↑ Header                          ↑ Payload                                      ↑ Signature
```

**Header** - This identifies which algorithm is used to generate the signature. It's Base64Url-encoded JSON that typically looks like:

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

The algorithm `HS256` means HMAC with SHA-256, which is a symmetric algorithm. Both creating and verifying the token use the same secret key.

**Payload** - This contains the claims, which are statements about the user and additional metadata. Standard claims include:

```json
{
  "sub": "alice@example.com",  // Subject (who the token is about)
  "exp": 1670000000,            // Expiration time (Unix timestamp)
  "iat": 1669996400             // Issued at (Unix timestamp)
}
```

The `sub` (subject) claim typically identifies the user. We'll use the email address. The `exp` (expiration) claim tells us when the token expires - after this time, the token should be rejected even if the signature is valid.

**Signature** - This is the cryptographic proof that the token hasn't been tampered with. It's created by:

1. Taking the encoded header and encoded payload
2. Combining them with a dot: `encodedHeader.encodedPayload`
3. Signing this string with your secret key using the algorithm specified in the header

```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

If someone tries to change the payload (say, modifying the email from "alice@example.com" to "admin@example.com"), the signature won't match anymore. When the server recalculates the signature using its secret key, it'll get a different result, and the token will be rejected.

### How JWT Authentication Works

Here's the complete flow from login to accessing protected resources:

**Login Flow:**
1. User sends email and password to `POST /login`
2. Server verifies the password against the stored hash
3. If correct, server creates a JWT containing the user's email
4. Server signs the JWT with a secret key
5. Server returns the JWT to the client
6. Client stores the JWT (usually in memory or localStorage)

**Accessing Protected Resources:**
1. Client wants to access `GET /users/me`
2. Client includes JWT in the Authorization header: `Bearer <token>`
3. Server extracts the token from the header
4. Server verifies the signature using the same secret key
5. If signature is valid, server decodes the payload to get the user's email
6. Server looks up the user in the database
7. Server returns the requested resource

**Why This Is Secure:**

Without the secret key, an attacker cannot create valid tokens. Even if they intercept a token, they can only use it until it expires - they can't modify it or create new ones. The signature ensures integrity (data hasn't been altered) and authenticity (it was created by someone with the secret key).

### JWT vs Session-Based Authentication

In traditional session-based authentication, when a user logs in, the server creates a session ID and stores session data in memory or a database. The session ID is sent to the client (usually as a cookie), and on each request, the server looks up the session to verify the user.

```
Session-Based:
Client                  Server                    Database
  │                      │                           │
  ├──Login───────────────>│                           │
  │                      ├─Check password───────────>│
  │                      │<────User data─────────────┤
  │                      ├─Create session───────────>│ (Store in Redis/DB)
  │<───Session ID────────┤                           │
  │                      │                           │
  ├──Request + Cookie───>│                           │
  │                      ├─Lookup session───────────>│
  │                      │<────Session data──────────┤
  │<───Response──────────┤                           │
```

With JWT:

```
JWT-Based:
Client                  Server                    Database
  │                      │                           │
  ├──Login───────────────>│                           │
  │                      ├─Check password───────────>│
  │                      │<────User data─────────────┤
  │                      │ (Create JWT, no storage)   │
  │<───JWT───────────────┤                           │
  │                      │                           │
  ├──Request + JWT──────>│                           │
  │                      │ (Verify signature)         │
  │                      ├─Optional: Fetch user data>│ (Only if needed)
  │<───Response──────────┤                           │
```

The key difference is that JWT doesn't require server-side storage. This makes it scalable - your API can handle millions of requests without maintaining session state. It also works great for microservices where multiple servers handle requests and you don't want to share session storage between them.

However, JWT has tradeoffs. Once issued, you can't revoke a JWT until it expires (unless you maintain a blacklist, which reintroduces state). Sessions can be invalidated immediately. JWT tokens are also larger than session IDs, increasing bandwidth usage. We'll explore these tradeoffs further in Lab 3 when we implement refresh tokens.

### Bearer Token Authentication

When sending a JWT to the server, we use the Bearer authentication scheme. The Authorization header looks like:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

The word "Bearer" indicates that whoever bears (possesses) this token should be granted access. It's like a concert ticket - whoever holds it gets in, regardless of who originally bought it. This is why you must keep your tokens secure and use HTTPS to prevent interception.

### Security Considerations

**Secret Key Management** - Your JWT secret key is like the master password for your entire authentication system. If it leaks, attackers can create valid tokens for any user. Never commit it to version control. Use environment variables and rotate it periodically.

**Token Expiration** - Always set an expiration time on your tokens. In this lab, we'll use 30 minutes. This limits the damage if a token is stolen - it becomes useless after expiring. In Lab 3, we'll implement refresh tokens to balance security with user convenience.

**HTTPS Only** - JWTs should only be transmitted over HTTPS. While the signature prevents tampering, the token is not encrypted - anyone who intercepts it can read the payload. More critically, they can use it to impersonate the user until it expires.

**Payload Sensitivity** - Don't put sensitive data in the JWT payload. It's Base64-encoded, not encrypted, so anyone can decode it and read the contents. Only include non-sensitive identifiers like user ID or email.

## Prerequisites

This lab builds directly on Lab 1. You'll need:

- Completed Lab 1 with working user registration
- PostgreSQL database with users table
- FastAPI application running with `/register` endpoint
- Virtual environment with all dependencies installed

If you haven't completed Lab 1, you can clone the starting code from:

```bash
git clone https://github.com/poridhioss/Building-Systems-With-FastAPI.git
cd Building-Systems-With-FastAPI/
git checkout -b mod-50/lab-1 origin/mod-50/lab-
```

Check `python --version` in the bash terminal of poridhi vm. If it does not work, then do the following:
```bash
sudo apt update
sudo apt install python3.12-venv -y
alias python=python3.12
source ~/.bashrc
```

## Project Structure

We'll add new files to our existing project:

```
Root directory
    ├── docker-compose.yml
    ├── .env                        # Add JWT_SECRET
    ├── .env.example
    ├── requirements.txt            # Add python-jose
    ├── alembic.ini
    ├── .gitignore
    │
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # Add login endpoint and protected route
    │   ├── database.py
    │   ├── models.py
    │   ├── schemas.py              # Add Token and UserLogin schemas
    │   ├── utils.py                # Add verify_password (already has get_password_hash)
    │   ├── auth.py                 # NEW: JWT functions and get_current_user
    │   └── config.py               # NEW: Configuration settings
    │
    └── alembic/
        └── versions/
```

## Step-by-Step Implementation Guide

### Step 1: Update Requirements

First, we need to add JWT support. Open `requirements.txt` and add:

```txt
fastapi==0.115.5
uvicorn[standard]==0.32.0
python-dotenv==1.0.1
SQLAlchemy==2.0.23
psycopg2-binary==2.9.10
pydantic==2.9.2
alembic==1.13.2
pydantic[email]
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-jose[cryptography]==3.3.0  # NEW: JWT support
```

The `python-jose` library provides JWT encoding and decoding with cryptographic signing. The `[cryptography]` extra includes the cryptography backend for better performance and security.

Install the new dependency:

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

### Step 2: Update Environment Variables

Add JWT configuration to your `.env` file:

```env
APP_NAME=FastAPI Auth Lab 2
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db
JWT_SECRET=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

The JWT_SECRET should be a long, random string. In production, generate it using:

```bash
openssl rand -hex 32
```

Also update `.env.example`:

```env
APP_NAME=FastAPI Auth Lab 2
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db
JWT_SECRET=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Step 3: Create Configuration Module

Create `app/config.py` to centralize configuration:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FastAPI Auth Lab 2")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


settings = Settings()
```

This pattern makes it easy to access configuration throughout your application. Instead of calling `os.getenv()` everywhere, you can just import `settings` and access `settings.JWT_SECRET`. It also provides default values and type hints, making your code more maintainable.

### Step 4: Update Utility Functions

<!-- We already have `get_password_hash()` from Lab 1. Now add the verification function to `app/utils.py`:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

The `verify_password()` function takes the password the user entered during login and the hashed password from your database. It hashes the plain password using the same salt that's embedded in the stored hash, then compares the results. If they match, the password is correct. -->

### Step 5: Update Pydantic Schemas

Add new schemas to `app/schemas.py`:

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
```

Let's break down these new schemas:

**UserLogin** - This is what the client sends to the `/login` endpoint. Just email and password, no validation beyond format. We'll verify the password against the database.

**Token** - This is what `/login` returns to the client. It contains the JWT in `access_token` and `token_type` which will always be "bearer". This matches the OAuth2 specification that FastAPI's security utilities expect.

**TokenData** - This is for internal use. When we decode a JWT, we'll extract the claims into this schema. The email might be None if the token is invalid or missing the subject claim.

### Step 6: Create Authentication Module

Create `app/auth.py` for all JWT-related functions:

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import User
from .schemas import TokenData


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

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


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, credentials_exception)

    user = db.query(User).filter(User.email == token_data.email).first()

    if user is None:
        raise credentials_exception

    return user
```

This is the heart of your authentication system. Let's walk through each function:

**oauth2_scheme** - This is a FastAPI utility that extracts the token from the Authorization header. When you use `token: str = Depends(oauth2_scheme)` in a route, FastAPI automatically looks for a header like `Authorization: Bearer <token>`, extracts the token part, and passes it to your function. If the header is missing or malformed, it returns a 401 error automatically.

**create_access_token()** - This creates a JWT. It takes a dictionary (typically containing the user's email as the "sub" claim) and an optional expiration time. If you don't provide expiration, it uses the default from your config (30 minutes). It adds the expiration as the "exp" claim, then uses `jwt.encode()` to create the token. The encoding process creates the header, base64-encodes it, base64-encodes the payload, concatenates them with a dot, and signs the whole thing with your secret key.

**verify_token()** - This decodes and validates a JWT. It uses `jwt.decode()` which verifies the signature and checks expiration automatically. If the signature is wrong or the token is expired, it raises a JWTError which we catch and convert to an HTTP exception. If the token is valid, we extract the email from the "sub" claim and return it wrapped in a TokenData schema.

**get_current_user()** - This is the authentication dependency you'll use on protected routes. It takes the token (extracted by oauth2_scheme), verifies it, extracts the email, and looks up the user in the database. If any step fails - token is invalid, user doesn't exist, etc. - it raises a 401 Unauthorized error. If everything succeeds, it returns the User object, which you can then use in your route handler.

The beauty of this design is that you can protect any route just by adding `current_user: User = Depends(get_current_user)` to its parameters. FastAPI handles all the dependency injection automatically.

### Step 7: Update Main Application

Now let's add the login endpoint and a protected route to `app/main.py`:

```python
import os
from datetime import timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import User
from .schemas import UserCreate, UserOut, UserLogin, Token
from .utils import get_password_hash, verify_password
from .auth import create_access_token, get_current_user
from .config import settings

load_dotenv()

app = FastAPI(
    title=settings.APP_NAME,
    description="User authentication with JWT",
    version="2.0.0"
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


@app.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == payload.email).first()

    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user
```

Let's examine the new endpoints:

**POST /login** - This is where users exchange their credentials for a JWT. First, we look up the user by email. If they don't exist, we return "Incorrect email or password" (not "User not found" - never reveal whether an email is in your system). Then we verify the password using our bcrypt utility. If it fails, same error message. We also check if the account is active - if it's been disabled, we return a 403 Forbidden error instead of 401. Finally, if everything checks out, we create a JWT with the user's email as the subject and return it along with the token type.

Notice we don't return the user's information here, just the token. The client stores this token and uses it for subsequent requests.

**GET /users/me** - This is a protected route demonstrating how authentication works. The `current_user: User = Depends(get_current_user)` parameter tells FastAPI to run the `get_current_user` function before executing this route. That function validates the JWT and returns the User object, which becomes available in our handler. We simply return that user object (Pydantic converts it to JSON using the UserOut schema).

The beauty is that if the token is invalid or missing, the user never reaches this function - FastAPI returns a 401 error automatically. Your route handler only runs if authentication succeeds.



### Step 8: Test the Login Flow


![alt text](image-1.png)
![alt text](image.png)

Start your application:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Set up your Poridhi Load Balancer as you did in Lab 1, then open Swagger UI at `<Load Balancer URL>/docs`.

**Test 1: Login with valid credentials**

Click on `POST /login`, then "Try it out". Enter:

```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

You should get a response like:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSIsImV4cCI6MTY3MDAwMDAwMH0...",
  "token_type": "bearer"
}
```

Copy that access token - you'll need it for the next test.

**Test 2: Access protected route**

Click on the lock icon at the top right of Swagger UI, or click on `GET /users/me` and then the "Authorize" button. Paste your access token (just the token part, not including "bearer") and click "Authorize".

Now execute `GET /users/me`. You should see:

```json
{
  "id": 1,
  "email": "alice@example.com",
  "is_active": true
}
```

**Test 3: Try accessing without authentication**

Log out in Swagger UI (click the lock icon and "Logout"). Try to execute `GET /users/me` again. You should get:

```json
{
  "detail": "Not authenticated"
}
```

**Test 4: Login with wrong password**

Try logging in with:

```json
{
  "email": "alice@example.com",
  "password": "WrongPassword"
}
```

You should get a 401 error:

```json
{
  "detail": "Incorrect email or password"
}
```

**Test 5: Login with non-existent email**

```json
{
  "email": "nonexistent@example.com",
  "password": "SomePassword"
}
```

Same 401 error. Notice we don't reveal whether the email exists - this prevents user enumeration attacks.

### Step 9: Test with curl

You can also test using curl from your command line:

**Login:**

```bash
curl -X POST "<Load Balancer URL>/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePass123!"
  }'
```

Save the access token from the response. Then access the protected route:

```bash
curl -X GET "<Load Balancer URL>/users/me" \
  -H "Authorization: Bearer <your_access_token_here>"
```

Try without the token:

```bash
curl -X GET "<Load Balancer URL>/users/me"
```

You'll get a 401 error.

Try with a malformed token:

```bash
curl -X GET "<Load Balancer URL>/users/me" \
  -H "Authorization: Bearer invalid.token.here"
```

You'll get a "Could not validate credentials" error.

### Step 10: Decode and Inspect a JWT

To understand what's inside your JWT, you can decode it manually. JWTs are just Base64-encoded strings, so you can decode them without the secret key (though you can't verify the signature without it).

Try this Python script:

```python
import json
import base64

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZUBleGFtcGxlLmNvbSIsImV4cCI6MTY3MDAwMDAwMH0..."

# Split the token
parts = token.split('.')

# Decode header (add padding if needed)
header = parts[0] + '=' * (4 - len(parts[0]) % 4)
decoded_header = base64.b64decode(header)
print("Header:", json.loads(decoded_header))

# Decode payload
payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
decoded_payload = base64.b64decode(payload)
print("Payload:", json.loads(decoded_payload))

# Signature is binary and can't be meaningfully decoded without the secret
print("\nSignature (hex):", parts[2][:20] + "...")
```

You'll see output like:

```
Header: {'alg': 'HS256', 'typ': 'JWT'}
Payload: {'sub': 'alice@example.com', 'exp': 1670000000}

Signature (hex): Kq1X8JJ5vY8pN2Q3R4...
```

You can also use online tools like jwt.io to decode tokens (but never paste production tokens into third-party websites!).

### Step 11: Verify Token Expiration

Let's verify that tokens actually expire. Temporarily change your token expiration to 1 minute in `.env`:

```env
ACCESS_TOKEN_EXPIRE_MINUTES=1
```

Restart your server and login to get a new token. Access `/users/me` immediately - it works. Wait 61 seconds, then try again. You should get:

```json
{
  "detail": "Could not validate credentials"
}
```

This happens because `jwt.decode()` automatically checks the "exp" claim and raises a JWTError if the token is expired. Your `verify_token()` function catches this and converts it to a 401 error.

Change the expiration back to 30 minutes for normal use:

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Step 12: Understanding the Request Lifecycle

Let's trace what happens when you call `GET /users/me` with a valid token:

1. **Client sends request:**
   ```
   GET /users/me
   Authorization: Bearer eyJhbGciOiJIUz...
   ```

2. **FastAPI processes dependencies:**
   - Sees `current_user: User = Depends(get_current_user)`
   - Runs `get_current_user()` before executing the route handler

3. **get_current_user() runs:**
   - Calls `oauth2_scheme` dependency first
   - OAuth2PasswordBearer extracts token from Authorization header
   - Passes token to `verify_token()`

4. **verify_token() validates:**
   - Calls `jwt.decode()` with secret key
   - Verifies signature matches
   - Checks expiration hasn't passed
   - Extracts email from "sub" claim
   - Returns TokenData(email="alice@example.com")

5. **get_current_user() continues:**
   - Queries database for user with that email
   - If found, returns User object
   - If not found, raises 401 error

6. **Route handler executes:**
   - Receives User object as `current_user` parameter
   - Returns user information

7. **FastAPI serializes response:**
   - Uses UserOut schema to convert User object to JSON
   - Excludes sensitive fields like hashed_password
   - Sends response to client

If any step fails (token missing, signature invalid, expired, user not found), the process stops and returns 401 Unauthorized. The route handler never executes.

### Step 13: Add More Protected Routes

Now that you have the authentication infrastructure, you can easily protect other routes. Let's add a few more examples to `app/main.py`:

```python
@app.get("/users/me/status")
def get_user_status(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "is_active": current_user.is_active,
        "message": f"Hello {current_user.email}! Your account is {'active' if current_user.is_active else 'inactive'}."
    }


@app.put("/users/me/deactivate")
def deactivate_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.is_active = False
    db.commit()

    return {"message": "Account deactivated successfully"}
```

Both routes are protected by the same `Depends(get_current_user)` dependency. You can add it to any route that should require authentication.

## Common Issues and Troubleshooting

**Issue 1: "Could not validate credentials" immediately after login**

This usually means your JWT_SECRET in the .env file doesn't match between encoding and decoding. Make sure you didn't change it between runs. Restart your server after changing environment variables.

**Issue 2: Token works in Swagger but not with curl**

Check your Authorization header format. It must be exactly:
```
Authorization: Bearer <token>
```

Note the space after "Bearer". Don't include quotes around the token.

**Issue 3: "Not authenticated" error**

This means the Authorization header is missing or malformed. Make sure you're including it in every request to protected routes.

**Issue 4: Login returns 401 for correct password**

Check that your database still has the user from Lab 1. Query it:

```bash
docker compose exec db psql -U postgres -d auth_lab1_db -c "SELECT email FROM users;"
```

If empty, register a new user first.

**Issue 5: Can't import jose**

Make sure you installed the cryptography extra:

```bash
pip install "python-jose[cryptography]"
```

The brackets might need escaping in some shells:

```bash
pip install 'python-jose[cryptography]'
```

## Security Best Practices

**Never log tokens** - Tokens are credentials. Logging them is like logging passwords. If you need to log authentication events, log the user ID or email, not the token.

**Use HTTPS in production** - JWTs are not encrypted, just Base64-encoded. Anyone who intercepts one can use it until it expires. Always use HTTPS to protect tokens in transit.

**Keep tokens short-lived** - The 30-minute expiration we're using is reasonable for most applications. For more sensitive operations, use shorter expiration times. We'll implement refresh tokens in Lab 3 to balance security with user experience.

**Validate on every request** - Never assume a token is valid just because it was valid before. Always validate the signature and expiration on every request.

**Protect your secret key** - Your JWT_SECRET is the key to your entire authentication system. Store it securely, never commit it to version control, and rotate it periodically. If it leaks, all existing tokens become compromised.

**Consider token revocation** - In this basic implementation, tokens can't be revoked before they expire. In production, you might maintain a blacklist of revoked tokens in Redis, or use refresh tokens (Lab 3) where you can revoke the refresh token to force re-authentication.

## Next Steps: Lab 3

In Lab 3, we'll enhance this system with:

- Refresh tokens for long-lived sessions
- Automatic token refresh without requiring re-login
- Token expiration handling on the client side
- Dual-token architecture (short-lived access + long-lived refresh)

These features make your authentication system production-ready while maintaining security.

## Conclusion

Congratulations! You've implemented a complete JWT authentication system. Your users can now register, login to receive a token, and use that token to access protected resources. You understand how JWTs work under the hood - the three-part structure, how signatures prevent tampering, and why expiration is critical for security.

You've also learned about FastAPI's dependency injection system and how to use it to create reusable authentication logic. The `get_current_user` dependency can protect any route simply by adding it to the function parameters. This makes your authentication system both secure and maintainable.

The authentication flow you've built is stateless - your server doesn't need to store sessions or lookup tokens in a database on every request. It just validates the cryptographic signature. This makes your API scalable and works great in distributed systems where multiple servers handle requests.

Ready for Lab 3? Let's implement refresh tokens and handle token expiration gracefully!
