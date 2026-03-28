from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api_schemas import ChatMessageCreate, PostCreate
from ..auth_dependencies import get_current_user
from ..business import leaderboard_rows, list_chat, list_feed
from ..db import get_db
from ..db_models import ChatMessage, CommunityPost, User

router = APIRouter(prefix="/api/v1/community", tags=["community"])


@router.get("/leaderboard")
def leaderboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    return {"items": leaderboard_rows(db)}


@router.get("/feed")
def get_feed(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    return {"items": list_feed(db, limit=limit)}


@router.post("/feed")
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    post = CommunityPost(user_id=user.id, content=payload.content.strip())
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"ok": True, "id": post.id}


@router.get("/chat")
def get_chat(
    since_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    return {"items": list_chat(db, since_id=since_id, limit=limit)}


@router.post("/chat")
def create_chat_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    msg = ChatMessage(user_id=user.id, content=payload.content.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"ok": True, "id": msg.id}
