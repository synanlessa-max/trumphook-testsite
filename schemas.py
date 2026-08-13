from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# --- Auth & User ---
class UserRegister(BaseModel):
    username: str
    password: str
    invite_code: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    uid: int
    username: str
    role: str
    invited_by: str
    is_banned: bool
    is_muted: bool
    created_at: str

    class Config:
        from_attributes = True

# --- Invites ---
class InviteResponse(BaseModel):
    id: int
    code: str
    created_by: str
    used_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- News ---
class NewsCreate(BaseModel):
    title: str
    content: str

class NewsResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Chat ---
class ChatMessageCreate(BaseModel):
    text: str

class ChatMessageResponse(BaseModel):
    id: int
    author: str
    role: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True