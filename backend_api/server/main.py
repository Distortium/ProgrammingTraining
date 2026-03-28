from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .business import bootstrap_data, cleanup_expired_sessions
from .config import settings
from .db import SessionLocal, engine
from .db_models import Base
from .docker_runner import run_user_code
from .logger_setup import setup_loggers
from .models import RunRequest, RunResponse
from .routers import admin, auth, community, courses, parent, practice, progress

app = FastAPI(title="Programmer API")
loggers = setup_loggers(settings)
LAN_ORIGIN_REGEX = (
    r"^https?://("
    r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
    r"10\.\d+\.\d+\.\d+|"
    r"192\.168\.\d+\.\d+|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+"
    r")(:\d+)?$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.frontend_origins if origin.strip()],
    allow_origin_regex=LAN_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    client_ip = request.client.host if request.client else "-"
    loggers.api.info(
        '%s "%s %s" %s %.2fms',
        client_ip,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_data(db)
        cleanup_expired_sessions(db)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/run", response_model=RunResponse)
def run_legacy(request: RunRequest) -> RunResponse:
    execution = run_user_code(request.language, request.code, settings, loggers.docker)
    return RunResponse(
        status=execution.status,
        stdout=execution.stdout,
        stderr=execution.stderr,
        exit_code=execution.exit_code,
        code_exec_time_ms=execution.code_exec_time_ms,
    )


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(progress.router)
app.include_router(practice.router)
app.include_router(parent.router)
app.include_router(community.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )

