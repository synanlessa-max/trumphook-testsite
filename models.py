from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from database import Base

class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # "owner", "admin", "user"
    invited_by = Column(String, default="System")
    is_banned = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_invite_at = Column(DateTime, nullable=True)

class InviteDB(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    created_by = Column(String, nullable=False)
    used_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class NewsDB(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    author = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatDB(Base):
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True, index=True)
    author = Column(String, nullable=False)
    role = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)