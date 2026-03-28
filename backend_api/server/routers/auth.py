from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api_schemas import LoginRequest, RegisterParentRequest, RegisterStudentRequest
from ..auth_dependencies import get_current_user
from ..business import ensure_first_login_achievement, user_progress_snapshot
from ..config import settings
from ..db import get_db
from ..db_models import User, UserRole
from ..security import clear_user_session, create_user_session, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register/student")
def register_student(payload: RegisterStudentRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT,
        age=payload.age,
        xp=0,
        level=1,
        stars=0,
        streak=1,
        lessons_completed=0,
        correct_answers=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    ensure_first_login_achievement(db, user)
    return {"ok": True, "user_id": user.id, "username": user.username, "role": user.role.value}


@router.post("/register/parent")
def register_parent(payload: RegisterParentRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.PARENT,
        age=None,
        xp=0,
        level=1,
        stars=0,
        streak=1,
        lessons_completed=0,
        correct_answers=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "user_id": user.id, "username": user.username, "role": user.role.value}


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_user_session(db, user)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.session_secure_cookie,
        path="/",
    )

    return {"ok": True, "user": {"id": user.id, "username": user.username, "role": user.role.value}}


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ = user
    clear_user_session(db, session_token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    snapshot = user_progress_snapshot(db, user)
    return snapshot
