from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import EmailStr, Field
from enum import Enum

class UserMode(str, Enum):
    NORMAL = "normal"
    AUDITOR = "auditor"

class User(Document):
    email: EmailStr
    full_name: str
    hashed_password: str 
    mode: UserMode = UserMode.NORMAL
    session_id: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        collection = "users"
        
    class Config:
        use_enum_values = True