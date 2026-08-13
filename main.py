import os
import uuid
from typing import List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
import schemas
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

# Создание таблиц при запуске
Base.metadata.create_all(bind=engine)

app = FastAPI(title="trumphook API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- АВТОРИЗАЦИЯ ---

@app.post("/api/auth/register", response_model=schemas.Token)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    user_count = db.query(models.UserDB).count()
    is_owner = (user_count == 0) or (user_data.username.lower() == "owner")

    if db.query(models.UserDB).filter(models.UserDB.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    inviter_name = "System"
    if not is_owner and user_count > 0:
        if not user_data.invite_code:
            raise HTTPException(status_code=400, detail="Invite code required")
        
        invite = db.query(models.InviteDB).filter(
            models.InviteDB.code == user_data.invite_code, 
            models.InviteDB.used_by == None
        ).first()
        
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid or used invite code")
        
        inviter_name = invite.created_by
        invite.used_by = user_data.username

    new_user = models.UserDB(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role="owner" if is_owner else "user",
        invited_by=inviter_name
    )
    db.add(new_user)
    db.commit()

    token = create_access_token({"sub": new_user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.UserDB).filter(models.UserDB.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="User is banned")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=schemas.UserResponse)
def get_me(current_user: models.UserDB = Depends(get_current_user)):
    return schemas.UserResponse(
        uid=current_user.id,
        username=current_user.username,
        role=current_user.role,
        invited_by=current_user.invited_by,
        is_banned=current_user.is_banned,
        is_muted=current_user.is_muted,
        created_at=current_user.created_at.strftime("%d/%m/%Y")
    )

# --- РАБОТА С DLL ---

@app.post("/api/admin/upload-dll")
def upload_dll(file: UploadFile = File(...), current_user: models.UserDB = Depends(get_current_user)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can upload DLL")

    file_path = os.path.join(UPLOAD_DIR, "trumphook.dll")
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    return {"message": "DLL successfully updated"}

@app.get("/api/download/dll")
def download_dll(current_user: models.UserDB = Depends(get_current_user)):
    file_path = os.path.join(UPLOAD_DIR, "trumphook.dll")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="DLL file not found on server")
    return FileResponse(file_path, filename="trumphook.dll", media_type="application/octet-stream")

# --- ИНВАЙТЫ ---

@app.post("/api/invites/generate")
def generate_invite(current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "user" and current_user.last_invite_at:
        if datetime.utcnow() - current_user.last_invite_at < timedelta(days=7):
            raise HTTPException(status_code=400, detail="You can generate 1 invite code every 7 days")

    code = f"TRUMP-{str(uuid.uuid4())[:8].upper()}"
    invite = models.InviteDB(code=code, created_by=current_user.username)
    
    current_user.last_invite_at = datetime.utcnow()
    db.add(invite)
    db.commit()
    return {"code": code}

@app.get("/api/invites/my", response_model=List[schemas.InviteResponse])
def get_my_invites(current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.InviteDB).filter(models.InviteDB.created_by == current_user.username).all()

# --- ЧАТ И НОВОСТИ ---

@app.get("/api/chat", response_model=List[schemas.ChatMessageResponse])
def get_chat(db: Session = Depends(get_db)):
    return db.query(models.ChatDB).order_by(models.ChatDB.created_at.asc()).limit(50).all()

@app.post("/api/chat")
def send_chat_msg(msg: schemas.ChatMessageCreate, current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_muted:
        raise HTTPException(status_code=403, detail="You are muted")

    chat_msg = models.ChatDB(author=current_user.username, role=current_user.role, text=msg.text)
    db.add(chat_msg)
    db.commit()
    return {"status": "ok"}

@app.get("/api/news", response_model=List[schemas.NewsResponse])
def get_news(db: Session = Depends(get_db)):
    return db.query(models.NewsDB).order_by(models.NewsDB.created_at.desc()).all()

@app.post("/api/news")
def post_news(news_data: schemas.NewsCreate, current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can publish news")

    news = models.NewsDB(title=news_data.title, content=news_data.content, author=current_user.username)
    db.add(news)
    db.commit()
    return {"status": "ok"}

# --- АДМИН-ПАНЕЛЬ ---

@app.get("/api/admin/users", response_model=List[schemas.UserResponse])
def get_users(current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    users = db.query(models.UserDB).all()
    return [
        schemas.UserResponse(
            uid=u.id,
            username=u.username,
            role=u.role,
            invited_by=u.invited_by,
            is_banned=u.is_banned,
            is_muted=u.is_muted,
            created_at=u.created_at.strftime("%d/%m/%Y")
        ) for u in users
    ]

@app.post("/api/admin/toggle-ban/{user_id}")
def toggle_ban(user_id: int, current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    target = db.query(models.UserDB).filter(models.UserDB.id == user_id).first()
    if target and target.role != "owner":
        target.is_banned = not target.is_banned
        db.commit()
    return {"status": "ok"}

@app.post("/api/admin/toggle-mute/{user_id}")
def toggle_mute(user_id: int, current_user: models.UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    target = db.query(models.UserDB).filter(models.UserDB.id == user_id).first()
    if target and target.role != "owner":
        target.is_muted = not target.is_muted
        db.commit()
    return {"status": "ok"}