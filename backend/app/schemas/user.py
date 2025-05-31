from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class UserMode(str, Enum):
    NORMAL = "normal"
    AUDITOR = "auditor"

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100) 
    full_name: Optional[str] = Field(..., min_length=2, max_length=100)
    user_mode: UserMode = UserMode.NORMAL

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserModeUpdate(BaseModel):
    user_mode: UserMode

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    user_mode: UserMode
    created_at: datetime
    last_login: Optional[datetime] = None
    # last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse