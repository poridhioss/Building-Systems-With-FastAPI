# Lambda-compatible FastAPI authentication API
# Uses in-memory storage instead of database

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from mangum import Mangum

# ========== Configuration ==========
JWT_SECRET = "lambda-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

# ========== FastAPI App ==========
app = FastAPI(
    title="Lambda Auth API",
    description="Serverless authentication API running on AWS Lambda",
    version="1.0.0"
)

# ========== Security ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ========== In-Memory Storage ==========
# In production, use RDS or DynamoDB
users_db = {}

# ========== Models ==========
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserOut(BaseModel):
    email: EmailStr

# ========== Helper Functions ==========
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

        if email not in users_db:
            raise credentials_exception

        return email

    except JWTError:
        raise credentials_exception

# ========== Endpoints ==========
@app.get("/")
def root():
    return {
        "message": "Lambda Auth API",
        "status": "running",
        "platform": "AWS Lambda"
    }

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}

@app.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate):
    if user.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
    users_db[user.email] = {
        "email": user.email,
        "hashed_password": hashed_password
    }

    return UserOut(email=user.email)

@app.post("/login", response_model=Token)
def login(user: UserLogin):
    if user.email not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    user_data = users_db[user.email]

    if not verify_password(user.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": user.email})

    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me", response_model=UserOut)
def get_me(email: str = Depends(get_current_user)):
    return UserOut(email=email)

# ========== Lambda Handler ==========
# This is what Lambda invokes
handler = Mangum(app, lifespan="off")