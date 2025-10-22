from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from .database import SessionLocal, engine, get_db
from .models import Base, User, License, Device
from .schemas import (
    UserCreate, UserResponse, LoginRequest, Token, TokenRefresh,
    LicenseCreate, LicenseResponse, DeviceCreate, DeviceResponse
)
from .auth import (
    get_password_hash, authenticate_user, create_access_token, 
    create_refresh_token, verify_token, get_current_active_user
)
import secrets

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WebPlay BTV API")

# Dev CORS (ajustar em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "file://",  # Para HTML local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "WebPlay BTV API"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar se usuário já existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Criar usuário
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/auth/login", response_model=Token)
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    payload = verify_token(token_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/auth/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.post("/licenses/issue", response_model=LicenseResponse)
def issue_license(payload: LicenseCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    key = secrets.token_urlsafe(16)
    lic = License(
        license_key=key,
        user_id=current_user.id,
        plan_name=payload.plan_name,
        max_devices=payload.max_devices,
        is_active=True,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic

@app.get("/licenses/me", response_model=List[LicenseResponse])
def list_licenses(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    licenses = db.query(License).filter(License.user_id == current_user.id).all()
    return licenses

@app.post("/devices/bind", response_model=DeviceResponse)
def bind_device(payload: DeviceCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.id == payload.license_id, License.user_id == current_user.id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    if not lic.is_active:
        raise HTTPException(status_code=400, detail="License inactive")
    current_count = db.query(Device).filter(Device.license_id == lic.id, Device.is_active == True).count()
    if current_count >= lic.max_devices:
        raise HTTPException(status_code=400, detail="Max devices reached for this license")
    existing = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already bound")
    dev = Device(
        device_id=payload.device_id,
        device_name=payload.device_name,
        user_id=current_user.id,
        license_id=lic.id,
        is_active=True,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev

@app.get("/devices/me", response_model=List[DeviceResponse])
def list_devices(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    devices = db.query(Device).filter(Device.user_id == current_user.id).all()
    return devices