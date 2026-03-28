from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api_schemas import PracticeRunRequest
from ..auth_dependencies import get_current_user
from ..business import complete_lesson, evaluate_achievements, simple_practice_check
from ..config import settings
from ..docker_runner import run_user_code
from ..logger_setup import setup_loggers
from ..models import JobStatus, Language
from ..db import get_db
from ..db_models import Lesson, User

router = APIRouter(prefix="/api/v1/practice", tags=["practice"])

loggers = setup_loggers(settings)


@router.post("/run")
def run_practice(
    payload: PracticeRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    language = Language(payload.language)
    result = run_user_code(language, payload.code, settings, loggers.docker)

    response = {
        "status": result.status,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "code_exec_time_ms": result.code_exec_time_ms,
        "lesson_check_passed": None,
        "completion": None,
        "new_achievements": [],
    }

    if payload.lesson_id is None:
        return response

    lesson = db.get(Lesson, payload.lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if lesson.practice_language and lesson.practice_language != payload.language:
        raise HTTPException(status_code=400, detail="Language does not match lesson")

    if result.status != JobStatus.OK:
        response["lesson_check_passed"] = False
        return response

    passed = simple_practice_check(lesson, payload.code)
    response["lesson_check_passed"] = passed

    if passed:
        completion = complete_lesson(db, user, lesson)
        achievements = evaluate_achievements(db, user)
        response["completion"] = completion
        response["new_achievements"] = achievements

    return response
