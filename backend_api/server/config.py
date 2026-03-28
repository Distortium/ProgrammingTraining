from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://programmer:programmer@localhost:5432/programmer",
    )

    request_timeout_sec: int = int(os.getenv("REQUEST_TIMEOUT_SEC", "120"))
    docker_timeout_sec: int = int(os.getenv("DOCKER_TIMEOUT_SEC", "30"))

    docker_memory: str = os.getenv("DOCKER_MEMORY", "192m")
    docker_cpus: str = os.getenv("DOCKER_CPUS", "0.50")
    docker_pids_limit: int = int(os.getenv("DOCKER_PIDS_LIMIT", "64"))

    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "programmer_session")
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "24"))
    session_secure_cookie: bool = _as_bool(os.getenv("SESSION_SECURE_COOKIE"), False)

    frontend_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "FRONTEND_ORIGINS",
            "http://127.0.0.1:5500,http://localhost:5500",
        )
        .strip()
        .split(",")
    )

    temp_dir: Path = BASE_DIR / "temp_jobs"
    logs_dir: Path = BASE_DIR / "logs"

    python_image: str = os.getenv("PYTHON_RUNNER_IMAGE", "local-code-runner-python:latest")
    javascript_image: str = os.getenv(
        "JAVASCRIPT_RUNNER_IMAGE", "local-code-runner-javascript:latest"
    )
    csharp_image: str = os.getenv("CSHARP_RUNNER_IMAGE", "local-code-runner-csharp:latest")

    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin12345")


settings = Settings()

