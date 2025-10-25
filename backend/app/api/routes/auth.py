from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.db.session import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    Token,
    TokenRefresh,
    UserCreate,
    UserResponse,
)
from app.services.audit import audit_event
from app.services.auth import authenticate_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed_password, full_name=payload.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_event(db, user.id, action="register", resource="user", resource_id=user.id, request=request)
    return user


@router.post("/login", response_model=Token)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    *,
    request: Request,
):
    user = authenticate_user(db, payload.email, payload.password)

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    audit_event(db, user.id, action="login", resource="user", resource_id=user.id, request=request)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_token(payload: TokenRefresh, db: Session = Depends(get_db)):
    from app.core.security import verify_token

    token_data = verify_token(payload.refresh_token, "refresh")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    email = token_data.get("sub")
    user = get_user_by_email(db, email) if email else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_active_user)):
    return current_user
