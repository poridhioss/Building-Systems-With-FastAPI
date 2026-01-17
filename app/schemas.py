from pydantic import BaseModel, EmailStr, Field
from typing import Optional  # NEW in Lab 2


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


# ========== NEW IN LAB 2 ==========
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