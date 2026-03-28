import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    SYSTEM_ERROR = "system_error"


class RunRequest(BaseModel):
    language: Language
    code: str = Field(min_length=1, max_length=800)


class RunResponse(BaseModel):
    status: JobStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    code_exec_time_ms: int = 0


@dataclass
class Job:
    job_id: str
    language: Language
    code: str
    status: JobStatus = JobStatus.QUEUED
    result: Optional[RunResponse] = None
    done_event: asyncio.Event = field(default_factory=asyncio.Event)
