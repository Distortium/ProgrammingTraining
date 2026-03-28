from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api_schemas import QuizSubmitRequest
from ..auth_dependencies import get_current_user
from ..business import complete_lesson, evaluate_achievements, submit_quiz, user_progress_snapshot
from ..db import get_db
from ..db_models import Lesson, LessonType, User

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson_endpoint(
    lesson_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    completion = complete_lesson(db, user, lesson)
    achievements = evaluate_achievements(db, user)
    return {"completion": completion, "new_achievements": achievements}


@router.post("/quizzes/{lesson_id}/submit")
def submit_quiz_endpoint(
    lesson_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if lesson.lesson_type != LessonType.QUIZ:
        raise HTTPException(status_code=400, detail="Lesson is not a quiz")

    return submit_quiz(db, user, lesson, payload.answers)


@router.get("/me")
def my_progress(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return user_progress_snapshot(db, user)
