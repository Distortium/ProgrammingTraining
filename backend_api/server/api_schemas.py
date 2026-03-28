from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RegisterStudentRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    age: int = Field(ge=7, le=99)


class RegisterParentRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=4, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=4, max_length=128)


class QuizSubmitRequest(BaseModel):
    answers: dict[int, int] = Field(default_factory=dict)


class PracticeRunRequest(BaseModel):
    language: str = Field(pattern="^(python|javascript)$")
    code: str = Field(min_length=1, max_length=2000)
    lesson_id: int | None = None


class ParentRequestCreate(BaseModel):
    child_username: str = Field(min_length=3, max_length=64)


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class AdminCourseCreate(BaseModel):
    track: str = Field(pattern="^(python|javascript)$")
    title: str = Field(min_length=3, max_length=128)
    description: str = Field(min_length=3, max_length=5000)
    is_published: bool = True


class AdminCourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=128)
    description: str | None = Field(default=None, min_length=3, max_length=5000)
    is_published: bool | None = None


class AdminModuleCreate(BaseModel):
    course_id: int
    title: str = Field(min_length=2, max_length=128)
    description: str = Field(min_length=2, max_length=5000)
    difficulty: str = Field(default="easy", pattern="^(easy|medium|hard)$")
    color: str = Field(default="#06d6a0", min_length=4, max_length=16)
    emoji: str = Field(default="📦", min_length=1, max_length=16)
    unlock_xp: int = Field(default=0, ge=0)
    xp_reward: int = Field(default=20, ge=0)
    order_index: int = Field(default=1, ge=1)


class AdminModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=128)
    description: str | None = Field(default=None, min_length=2, max_length=5000)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    color: str | None = Field(default=None, min_length=4, max_length=16)
    emoji: str | None = Field(default=None, min_length=1, max_length=16)
    unlock_xp: int | None = Field(default=None, ge=0)
    xp_reward: int | None = Field(default=None, ge=0)
    order_index: int | None = Field(default=None, ge=1)


class AdminLessonCreate(BaseModel):
    module_id: int
    title: str = Field(min_length=2, max_length=128)
    lesson_type: str = Field(pattern="^(theory|quiz|practice)$")
    emoji: str = Field(default="📖", min_length=1, max_length=16)
    xp_reward: int = Field(default=10, ge=0)
    order_index: int = Field(default=1, ge=1)
    theory_html: str | None = None
    practice_task: str | None = None
    practice_starter: str | None = None
    practice_hint: str | None = None
    practice_language: str | None = Field(default=None, pattern="^(python|javascript)$")


class AdminLessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=128)
    emoji: str | None = Field(default=None, min_length=1, max_length=16)
    xp_reward: int | None = Field(default=None, ge=0)
    order_index: int | None = Field(default=None, ge=1)
    theory_html: str | None = None
    practice_task: str | None = None
    practice_starter: str | None = None
    practice_hint: str | None = None
    practice_language: str | None = Field(default=None, pattern="^(python|javascript)$")


class AdminQuestionCreate(BaseModel):
    lesson_id: int
    text: str = Field(min_length=3, max_length=2000)
    order_index: int = Field(default=1, ge=1)
    options: list[dict[str, Any]] = Field(default_factory=list)


class AdminQuestionUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=3, max_length=2000)
    order_index: int | None = Field(default=None, ge=1)
    options: list[dict[str, Any]] | None = None


class PracticeCheckUpdate(BaseModel):
    lesson_id: int
    practice_check_mode: str | None = Field(default=None, max_length=32)
    practice_check_value: str | None = None
