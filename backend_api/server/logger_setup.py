import logging
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
import sys

from .config import Settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


@dataclass(frozen=True)
class Loggers:
    docker: Logger
    api: Logger


def _build_file_logger(name: str, file_path: Path) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    return logger


def _build_console_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def setup_loggers(settings: Settings) -> Loggers:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    docker_logger = _build_file_logger(
        "docker_logger", settings.logs_dir / "docker_actions.log"
    )
    api_logger = _build_file_logger("api_logger", settings.logs_dir / "api_console.log")
    if not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in api_logger.handlers
    ):
        api_logger.addHandler(_build_console_handler())

    return Loggers(docker=docker_logger, api=api_logger)
