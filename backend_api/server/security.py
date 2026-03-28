from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .db_models import SessionToken, User


def _pbkdf2(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _pbkdf2(password, salt)
    return f"{salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt, digest = encoded.split("$", 1)
    except ValueError:
        return False
    expected = _pbkdf2(password, salt)
    return hmac.compare_digest(expected, digest)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hash_session_token(token)
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=settings.session_ttl_hours)

    db.add(
        SessionToken(
            token_hash=token_hash,
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
        )
    )
    db.commit()
    return token


def get_user_by_session_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    token_hash = hash_session_token(token)
    row = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash))
    if row is None:
        return None
    if row.expires_at <= datetime.utcnow():
        db.execute(delete(SessionToken).where(SessionToken.id == row.id))
        db.commit()
        return None
    return db.get(User, row.user_id)


def clear_user_session(db: Session, token: str | None) -> None:
    if not token:
        return
    token_hash = hash_session_token(token)
    db.execute(delete(SessionToken).where(SessionToken.token_hash == token_hash))
    db.commit()
