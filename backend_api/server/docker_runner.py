import shlex
import subprocess
import time
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory

from .config import Settings
from .models import JobStatus, Language


@dataclass
class DockerExecutionResult:
    status: JobStatus
    stdout: str
    stderr: str
    exit_code: int
    code_exec_time_ms: int


def _get_code_file_name(language: Language) -> str:
    if language == Language.PYTHON:
        return "main.py"
    if language == Language.JAVASCRIPT:
        return "main.js"
    raise ValueError(f"Unsupported language: {language}")


def _get_image_name(language: Language, settings: Settings) -> str:
    if language == Language.PYTHON:
        return settings.python_image
    if language == Language.JAVASCRIPT:
        return settings.javascript_image
    raise ValueError(f"Unsupported language: {language}")


def _prepare_source_code(language: Language, code: str) -> str:
    _ = language
    return code.replace("\r\n", "\n")


def _is_infra_docker_error(exit_code: int, stderr: str) -> bool:
    if exit_code in {125, 126, 127}:
        return True

    lower_stderr = stderr.lower()
    infra_markers = [
        "cannot connect to the docker daemon",
        "failed to connect to the docker api",
        "is the docker daemon running",
        "error response from daemon",
        "docker desktop",
    ]
    return any(marker in lower_stderr for marker in infra_markers)


def _run_command(command: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        check=False,
    )


def _force_remove_container(container_id: str, docker_logger: Logger) -> None:
    if not container_id:
        return
    cleanup_cmd = ["docker", "rm", "-f", container_id]
    try:
        completed = subprocess.run(
            cleanup_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            docker_logger.warning(
                "Docker cleanup failed for container=%s stderr=%s",
                container_id,
                (completed.stderr or "").strip(),
            )
    except Exception as exc:  # noqa: BLE001
        docker_logger.warning(
            "Docker cleanup exception for container=%s error=%s", container_id, exc
        )


def run_user_code(
    language: Language, code: str, settings: Settings, docker_logger: Logger
) -> DockerExecutionResult:
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    code_file_name = _get_code_file_name(language)
    image_name = _get_image_name(language, settings)

    with TemporaryDirectory(dir=settings.temp_dir) as temp_dir:
        temp_dir_path = Path(temp_dir)
        source_file_path = temp_dir_path / code_file_name
        prepared_code = _prepare_source_code(language, code)
        source_file_path.write_text(prepared_code, encoding="utf-8")

        target_path_in_container = f"/workspace/{code_file_name}"
        create_command = [
            "docker",
            "create",
            "--network",
            "none",
            "--memory",
            settings.docker_memory,
            "--cpus",
            settings.docker_cpus,
            "--pids-limit",
            str(settings.docker_pids_limit),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=16m",
            image_name,
        ]

        docker_logger.info(
            "Docker create started: language=%s image=%s file=%s",
            language.value,
            image_name,
            source_file_path,
        )
        docker_logger.info("Docker create command: %s", shlex.join(create_command))

        container_id = ""
        try:
            create_result = _run_command(create_command, settings.docker_timeout_sec)
            if create_result.returncode != 0:
                stderr = create_result.stderr or ""
                docker_logger.error(
                    "Docker create failed: exit_code=%s stderr=%s",
                    create_result.returncode,
                    stderr.strip(),
                )
                return DockerExecutionResult(
                    status=JobStatus.SYSTEM_ERROR,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    code_exec_time_ms=0,
                )

            container_id = (create_result.stdout or "").strip()
            if not container_id:
                docker_logger.error("Docker create returned empty container id.")
                return DockerExecutionResult(
                    status=JobStatus.SYSTEM_ERROR,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    code_exec_time_ms=0,
                )

            copy_command = [
                "docker",
                "cp",
                str(source_file_path),
                f"{container_id}:{target_path_in_container}",
            ]
            docker_logger.info("Docker copy command: %s", shlex.join(copy_command))
            copy_result = _run_command(copy_command, settings.docker_timeout_sec)
            if copy_result.returncode != 0:
                docker_logger.error(
                    "Docker copy failed: exit_code=%s stderr=%s",
                    copy_result.returncode,
                    (copy_result.stderr or "").strip(),
                )
                return DockerExecutionResult(
                    status=JobStatus.SYSTEM_ERROR,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    code_exec_time_ms=0,
                )

            start_command = ["docker", "start", "-a", container_id]
            docker_logger.info("Docker start command: %s", shlex.join(start_command))
            exec_start = time.perf_counter()
            completed = _run_command(start_command, settings.docker_timeout_sec)
            exec_time_ms = int((time.perf_counter() - exec_start) * 1000)
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""

            docker_logger.info(
                "Docker run finished: container=%s exit_code=%s exec_time_ms=%s",
                container_id,
                completed.returncode,
                exec_time_ms,
            )

            if completed.returncode == 0:
                status = JobStatus.OK
            elif _is_infra_docker_error(completed.returncode, stderr):
                docker_logger.error(
                    "Docker infrastructure error detected: exit_code=%s stderr=%s",
                    completed.returncode,
                    stderr.strip(),
                )
                return DockerExecutionResult(
                    status=JobStatus.SYSTEM_ERROR,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    code_exec_time_ms=0,
                )
            else:
                status = JobStatus.RUNTIME_ERROR

            return DockerExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=completed.returncode,
                code_exec_time_ms=exec_time_ms,
            )
        except subprocess.TimeoutExpired:
            docker_logger.info("Docker timeout: %ss", settings.docker_timeout_sec)
            _force_remove_container(container_id, docker_logger)
            return DockerExecutionResult(
                status=JobStatus.TIMEOUT,
                stdout="",
                stderr="",
                exit_code=-1,
                code_exec_time_ms=0,
            )
        except FileNotFoundError:
            error_text = (
                "Docker CLI was not found. Install Docker Desktop and add docker to PATH."
            )
            docker_logger.exception(error_text)
            return DockerExecutionResult(
                status=JobStatus.SYSTEM_ERROR,
                stdout="",
                stderr="",
                exit_code=-1,
                code_exec_time_ms=0,
            )
        except Exception as exc:  # noqa: BLE001
            docker_logger.exception("Docker system error: %s", exc)
            return DockerExecutionResult(
                status=JobStatus.SYSTEM_ERROR,
                stdout="",
                stderr="",
                exit_code=-1,
                code_exec_time_ms=0,
            )
        finally:
            _force_remove_container(container_id, docker_logger)
