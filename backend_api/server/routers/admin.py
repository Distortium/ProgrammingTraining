from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..api_schemas import (
    AdminCourseCreate,
    AdminCourseUpdate,
    AdminLessonCreate,
    AdminLessonUpdate,
    AdminModuleCreate,
    AdminModuleUpdate,
    AdminQuestionCreate,
    AdminQuestionUpdate,
    PracticeCheckUpdate,
)
from ..auth_dependencies import require_role
from ..business import serialize_course
from ..db import get_db
from ..db_models import Course, Lesson, LessonType, Module, QuizOption, QuizQuestion, User, UserRole

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

DEFAULT_PRACTICE_STARTERS = {
    "python": 'name = "Programmer"\nprint(f"Привет, {name}!")\n',
    "javascript": "const name = 'Programmer';\nconsole.log(`Привет, ${name}!`);\n",
    "csharp": 'using System;\n\nstring name = "Programmer";\nConsole.WriteLine($"Привет, {name}!");\n',
}
DEFAULT_PRACTICE_HINTS = {
    "python": "Используй переменные, print и условия из теории.",
    "javascript": "Используй переменные, функцию и console.log.",
    "csharp": "Используй переменные, Console.WriteLine и if/else при необходимости.",
}


def _apply_updates(model, data: dict) -> None:
    for key, value in data.items():
        if value is not None:
            setattr(model, key, value)


def _next_order_index(db: Session, model, fk_field_name: str, fk_value: int) -> int:
    fk_field = getattr(model, fk_field_name)
    current_max = db.scalar(select(func.max(model.order_index)).where(fk_field == fk_value)) or 0
    return int(current_max) + 1


def _practice_defaults(language: str) -> tuple[str, str]:
    starter = DEFAULT_PRACTICE_STARTERS.get(language, DEFAULT_PRACTICE_STARTERS["python"])
    hint = DEFAULT_PRACTICE_HINTS.get(language, DEFAULT_PRACTICE_HINTS["python"])
    return starter, hint


@router.get("/courses")
def admin_courses(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    courses = db.scalars(select(Course).order_by(Course.id)).all()
    return {"items": [serialize_course(db, c, include_answers=True) for c in courses]}


@router.post("/courses")
def create_course(
    payload: AdminCourseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    course = Course(
        track=payload.track,
        title=payload.title,
        description=payload.description,
        is_published=payload.is_published,
        created_by=admin.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"ok": True, "id": course.id}


@router.put("/courses/{course_id}")
def update_course(
    course_id: int,
    payload: AdminCourseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    _apply_updates(course, payload.model_dump())
    db.commit()
    return {"ok": True}


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"ok": True}


@router.post("/modules")
def create_module(
    payload: AdminModuleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail="Course not found")
    values = payload.model_dump()
    order_index = int(values.get("order_index") or 1)
    order_taken = db.scalar(
        select(Module.id).where(Module.course_id == payload.course_id, Module.order_index == order_index)
    )
    values["order_index"] = (
        _next_order_index(db, Module, "course_id", payload.course_id)
        if order_taken is not None
        else order_index
    )
    module = Module(**values)
    db.add(module)
    db.commit()
    db.refresh(module)
    return {"ok": True, "id": module.id, "order_index": module.order_index}


@router.put("/modules/{module_id}")
def update_module(
    module_id: int,
    payload: AdminModuleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _apply_updates(module, payload.model_dump())
    db.commit()
    return {"ok": True}


@router.delete("/modules/{module_id}")
def delete_module(
    module_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    module = db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    db.delete(module)
    db.commit()
    return {"ok": True}


@router.post("/lessons")
def create_lesson(
    payload: AdminLessonCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    module = db.get(Module, payload.module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    values = payload.model_dump()
    lesson_type = LessonType(values["lesson_type"])
    values["lesson_type"] = lesson_type

    order_index = int(values.get("order_index") or 1)
    order_taken = db.scalar(
        select(Lesson.id).where(Lesson.module_id == payload.module_id, Lesson.order_index == order_index)
    )
    values["order_index"] = (
        _next_order_index(db, Lesson, "module_id", payload.module_id)
        if order_taken is not None
        else order_index
    )

    if lesson_type == LessonType.THEORY and not (values.get("theory_html") or "").strip():
        raise HTTPException(status_code=400, detail="Theory lesson requires theory_html")

    if lesson_type == LessonType.PRACTICE:
        if not (values.get("practice_task") or "").strip():
            raise HTTPException(status_code=400, detail="Practice lesson requires practice_task")
        if not values.get("practice_language"):
            course = db.get(Course, module.course_id)
            values["practice_language"] = course.track if course else "python"
        default_starter, default_hint = _practice_defaults(values["practice_language"])
        if not (values.get("practice_starter") or "").strip():
            values["practice_starter"] = default_starter
        if not (values.get("practice_hint") or "").strip():
            values["practice_hint"] = default_hint
        values["theory_html"] = None
    else:
        values["practice_task"] = None
        values["practice_starter"] = None
        values["practice_hint"] = None
        values["practice_language"] = None

    lesson = Lesson(**values)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return {"ok": True, "id": lesson.id, "order_index": lesson.order_index}


@router.put("/lessons/{lesson_id}")
def update_lesson(
    lesson_id: int,
    payload: AdminLessonUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _apply_updates(lesson, payload.model_dump())
    db.commit()
    return {"ok": True}


@router.delete("/lessons/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    db.delete(lesson)
    db.commit()
    return {"ok": True}


@router.post("/questions")
def create_question(
    payload: AdminQuestionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    lesson = db.get(Lesson, payload.lesson_id)
    if lesson is None or lesson.lesson_type != LessonType.QUIZ:
        raise HTTPException(status_code=404, detail="Quiz lesson not found")

    if not payload.options:
        raise HTTPException(status_code=400, detail="Question requires options")

    normalized_options = []
    for idx, item in enumerate(payload.options, 1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized_options.append(
            {
                "text": text,
                "is_correct": bool(item.get("is_correct", False)),
                "order_index": int(item.get("order_index", idx)),
            }
        )

    if len(normalized_options) < 2:
        raise HTTPException(status_code=400, detail="Question requires at least two non-empty options")
    if not any(option["is_correct"] for option in normalized_options):
        raise HTTPException(status_code=400, detail="At least one option must be marked as correct")

    order_index = int(payload.order_index)
    order_taken = db.scalar(
        select(QuizQuestion.id).where(
            QuizQuestion.lesson_id == payload.lesson_id,
            QuizQuestion.order_index == order_index,
        )
    )
    if order_taken is not None:
        order_index = _next_order_index(db, QuizQuestion, "lesson_id", payload.lesson_id)

    question = QuizQuestion(lesson_id=payload.lesson_id, text=payload.text, order_index=order_index)
    db.add(question)
    db.flush()

    for idx, item in enumerate(normalized_options, 1):
        db.add(
            QuizOption(
                question_id=question.id,
                text=item["text"],
                is_correct=item["is_correct"],
                order_index=idx,
            )
        )

    db.commit()
    db.refresh(question)
    return {"ok": True, "id": question.id, "order_index": question.order_index}


@router.put("/questions/{question_id}")
def update_question(
    question_id: int,
    payload: AdminQuestionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    question = db.get(QuizQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if payload.text is not None:
        question.text = payload.text
    if payload.order_index is not None:
        question.order_index = payload.order_index

    if payload.options is not None:
        db.execute(delete(QuizOption).where(QuizOption.question_id == question.id))
        for idx, item in enumerate(payload.options, 1):
            db.add(
                QuizOption(
                    question_id=question.id,
                    text=str(item.get("text", "")),
                    is_correct=bool(item.get("is_correct", False)),
                    order_index=int(item.get("order_index", idx)),
                )
            )

    db.commit()
    return {"ok": True}


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    q = db.get(QuizQuestion, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    return {"ok": True}


@router.post("/practice-checks")
def set_practice_check(
    payload: PracticeCheckUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    _ = admin
    lesson = db.get(Lesson, payload.lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson.practice_check_mode = payload.practice_check_mode
    lesson.practice_check_value = payload.practice_check_value
    db.commit()
    return {"ok": True}

