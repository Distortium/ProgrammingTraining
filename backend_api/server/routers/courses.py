from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth_dependencies import get_current_user
from ..business import serialize_course
from ..db import get_db
from ..db_models import Course, User

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


@router.get("")
def list_courses(
    track: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    query = select(Course).where(Course.is_published.is_(True))
    if track:
        query = query.where(Course.track == track)
    courses = db.scalars(query.order_by(Course.id)).all()
    return {"items": [serialize_course(db, c, include_answers=False) for c in courses]}


@router.get("/{course_id}")
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ = user
    course = db.get(Course, course_id)
    if course is None or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found")
    return serialize_course(db, course, include_answers=False)
